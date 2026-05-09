from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from time import monotonic, sleep
import webbrowser

from flask import Flask, Response, jsonify, render_template, request

from src.game.board import AI, EMPTY, HUMAN, winning_line, winner
from src.game.minimax import SearchResult, move_for_difficulty
from src.vision.face_detector import FaceDetector

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


@dataclass
class Match:
    board: list[str]
    current_player: str
    difficulty: str
    starter: str
    game_over: bool
    message: str
    metrics: dict[str, object]
    last_move: int | None = None


class GameService:
    def __init__(self) -> None:
        self.lock = Lock()
        self.match = Match(
            board=[EMPTY for _ in range(9)],
            current_player=HUMAN,
            difficulty="imposible",
            starter="humano",
            game_over=False,
            message="Mira a la camara para activar tu turno.",
            metrics={"mode": "imposible", "nodes": 0, "elapsed_ms": 0.0, "score": 0},
        )

    def reset(self, starter: str = "humano", difficulty: str = "imposible") -> Match:
        with self.lock:
            self.match = Match(
                board=[EMPTY for _ in range(9)],
                current_player=AI if starter == "ia" else HUMAN,
                difficulty=difficulty,
                starter=starter,
                game_over=False,
                message="Nueva partida. La IA inicia." if starter == "ia" else "Nueva partida. Esperando rostro.",
                metrics={"mode": difficulty, "nodes": 0, "elapsed_ms": 0.0, "score": 0},
            )
            if starter == "ia":
                self._ai_move_locked()
            return self.match

    def state(self) -> Match:
        with self.lock:
            return self.match

    def human_move(self, index: int, face_present: bool, camera_gate: bool) -> tuple[bool, str, Match]:
        with self.lock:
            if self.match.game_over:
                return False, "La partida ya finalizo.", self.match
            if self.match.current_player != HUMAN:
                return False, "Es turno de la IA.", self.match
            if camera_gate and not face_present:
                return False, "Acerca tu rostro a la camara para habilitar el turno.", self.match
            if index < 0 or index > 8 or self.match.board[index] != EMPTY:
                return False, "Casilla no disponible.", self.match

            self.match.board[index] = HUMAN
            self.match.last_move = index
            self._resolve_locked()
            if not self.match.game_over:
                self.match.current_player = AI
                self._ai_move_locked()
            return True, self.match.message, self.match

    def _ai_move_locked(self) -> None:
        result = move_for_difficulty(self.match.board, self.match.difficulty)
        if result.position is not None:
            self.match.board[result.position] = AI
            self.match.last_move = result.position

        self.match.metrics = _metrics(self.match.difficulty, result)
        self._resolve_locked()
        if not self.match.game_over:
            self.match.current_player = HUMAN
            self.match.message = "Tu turno. El tablero se habilita al detectar tu rostro."

    def _resolve_locked(self) -> None:
        state = winner(self.match.board)
        if state is None:
            return

        self.match.game_over = True
        if state == AI:
            self.match.message = "Gano la IA. En modo imposible solo ocurre si el humano deja una linea forzada."
        elif state == HUMAN:
            self.match.message = "Gano el humano. Esto puede ocurrir en facil o normal."
        else:
            self.match.message = "Empate perfecto. Resultado esperado en modo imposible."


class CameraService:
    def __init__(self) -> None:
        self.detector = FaceDetector()
        self.lock = Lock()
        self.face_present = False
        self.message = "Inicializando camara..."
        self.last_seen_at = 0.0
        self.camera_gate = True

    def set_gate(self, enabled: bool) -> None:
        self.camera_gate = enabled

    def read(self):
        with self.lock:
            detection = self.detector.read()
            self.message = detection.message
            self.face_present = detection.face_present
            if detection.face_present:
                self.last_seen_at = monotonic()
            return detection

    def recent_face(self) -> bool:
        if not self.camera_gate:
            return True
        return self.face_present or (monotonic() - self.last_seen_at) < 1.2

    def close(self) -> None:
        self.detector.stop()


game = GameService()
camera = CameraService()


def _metrics(difficulty: str, result: SearchResult) -> dict[str, object]:
    return {
        "mode": difficulty,
        "nodes": result.nodes,
        "elapsed_ms": round(result.elapsed_ms, 3),
        "score": result.score,
        "position": result.position,
    }


def _payload(match: Match) -> dict[str, object]:
    return {
        **asdict(match),
        "winner": winner(match.board),
        "winning_line": winning_line(match.board),
        "face_present": camera.recent_face(),
        "face_message": camera.message,
        "camera_gate": camera.camera_gate,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    return jsonify(_payload(game.state()))


@app.post("/api/new-game")
def api_new_game():
    data = request.get_json(silent=True) or {}
    starter = data.get("starter", "humano")
    difficulty = data.get("difficulty", "imposible")
    match = game.reset(starter=starter, difficulty=difficulty)
    return jsonify(_payload(match))


@app.post("/api/settings")
def api_settings():
    data = request.get_json(silent=True) or {}
    camera.set_gate(bool(data.get("camera_gate", True)))
    return jsonify(_payload(game.state()))


@app.post("/api/move")
def api_move():
    data = request.get_json(silent=True) or {}
    ok, message, match = game.human_move(
        index=int(data.get("index", -1)),
        face_present=camera.recent_face(),
        camera_gate=camera.camera_gate,
    )
    response = _payload(match)
    response["ok"] = ok
    response["notice"] = message
    return jsonify(response), 200 if ok else 400


@app.get("/api/face")
def api_face():
    camera.read()
    return jsonify(
        {
            "face_present": camera.recent_face(),
            "message": camera.message,
            "camera_gate": camera.camera_gate,
        }
    )


@app.get("/video-feed")
def video_feed():
    return Response(_frame_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


def _frame_stream():
    while True:
        detection = camera.read()
        frame = detection.frame
        if frame is not None and camera.detector.cv2 is not None:
            cv2 = camera.detector.cv2
            preview = frame.copy()
            for x, y, w, h in detection.faces:
                cv2.rectangle(preview, (x, y), (x + w, y + h), (225, 29, 72), 3)
                cv2.putText(
                    preview,
                    "ROSTRO",
                    (x, max(26, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (20, 20, 20),
                    2,
                )
            ok, encoded = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n"
        sleep(0.08)


def main() -> None:
    url = "http://127.0.0.1:5000"
    print(f"Servidor web iniciado en {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)


if __name__ == "__main__":
    main()
