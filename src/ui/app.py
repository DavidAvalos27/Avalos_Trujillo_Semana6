from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from src.game.board import AI, EMPTY, HUMAN, WIN_LINES, winning_line, winner
from src.game.minimax import SearchResult, best_move
from src.vision.face_detector import FaceDetector

try:
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover - depends on local install
    Image = None
    ImageTk = None


@dataclass
class Palette:
    background: str = "#07111f"
    panel: str = "#0e1f35"
    panel_light: str = "#17385b"
    text: str = "#f6fbff"
    muted: str = "#9fb4cc"
    cyan: str = "#2ee6ff"
    green: str = "#66f2a5"
    pink: str = "#ff4fd8"
    orange: str = "#ffb84d"
    red: str = "#ff5c7a"
    grid: str = "#315b84"
    cell: str = "#102944"
    cell_hover: str = "#193e63"


class TicTacToeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.palette = Palette()
        self.title("Tres en Raya IA Invencible - Minimax + OpenCV")
        self.geometry("1180x760")
        self.minsize(1020, 680)
        self.configure(bg=self.palette.background)

        self.board = [EMPTY for _ in range(9)]
        self.current_player = HUMAN
        self.human_can_play = False
        self.game_over = False
        self.ai_starts = False
        self.last_move: int | None = None
        self.hover_cell: int | None = None
        self.last_result: SearchResult | None = None
        self.last_plain_result: SearchResult | None = None
        self.camera_enabled = tk.BooleanVar(value=True)
        self.status_text = tk.StringVar(value="Mira a la camara para activar tu turno.")
        self.face_text = tk.StringVar(value="Inicializando camara...")
        self.metrics_text = tk.StringVar(value="La metrica aparecera despues del primer movimiento de IA.")
        self.score_text = tk.StringVar(value="Humano O  |  IA X")
        self.turn_text = tk.StringVar(value="Turno humano")

        self.detector = FaceDetector()
        self._camera_photo = None
        self._build_style()
        self._build_layout()
        self._draw_board()
        self.after(300, self._vision_loop)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Modern.TButton",
            background=self.palette.panel_light,
            foreground=self.palette.text,
            borderwidth=0,
            focusthickness=0,
            padding=(16, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Modern.TButton",
            background=[("active", self.palette.cyan), ("pressed", self.palette.green)],
            foreground=[("active", self.palette.background), ("pressed", self.palette.background)],
        )
        style.configure(
            "Modern.TCheckbutton",
            background=self.palette.background,
            foreground=self.palette.text,
            font=("Segoe UI", 10, "bold"),
        )

    def _build_layout(self) -> None:
        root = tk.Frame(self, bg=self.palette.background)
        root.pack(fill="both", expand=True, padx=24, pady=22)
        root.columnconfigure(0, weight=3)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(1, weight=1)

        header = tk.Frame(root, bg=self.palette.background)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        tk.Label(
            header,
            text="Tres en Raya Invencible",
            bg=self.palette.background,
            fg=self.palette.text,
            font=("Segoe UI", 28, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="Minimax + Poda Alfa-Beta + OpenCV",
            bg=self.palette.background,
            fg=self.palette.cyan,
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left", padx=(18, 0), pady=(9, 0))

        board_panel = tk.Frame(root, bg=self.palette.background)
        board_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 22))
        board_panel.rowconfigure(0, weight=1)
        board_panel.columnconfigure(0, weight=1)

        self.board_canvas = tk.Canvas(
            board_panel,
            width=610,
            height=610,
            bg=self.palette.background,
            highlightthickness=0,
        )
        self.board_canvas.grid(row=0, column=0, sticky="nsew")
        self.board_canvas.bind("<Button-1>", self._on_board_click)
        self.board_canvas.bind("<Motion>", self._on_board_motion)
        self.board_canvas.bind("<Leave>", self._on_board_leave)

        side = tk.Frame(root, bg=self.palette.background)
        side.grid(row=1, column=1, sticky="nsew")
        side.columnconfigure(0, weight=1)

        self._info_card(side, "Estado", self.status_text, 0, accent=self.palette.green)
        self._info_card(side, "Turno", self.turn_text, 1, accent=self.palette.cyan)
        self._camera_card(side, 2)
        self._info_card(side, "Rendimiento IA", self.metrics_text, 3, accent=self.palette.orange)

        controls = tk.Frame(side, bg=self.palette.background)
        controls.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        controls.columnconfigure((0, 1), weight=1)
        ttk.Button(controls, text="Nueva partida", style="Modern.TButton", command=self.reset_game).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(controls, text="IA inicia", style="Modern.TButton", command=self.toggle_starter).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )
        ttk.Checkbutton(
            controls,
            text="Camara activa",
            variable=self.camera_enabled,
            style="Modern.TCheckbutton",
            command=self._toggle_camera,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(14, 0))

    def _info_card(
        self,
        parent: tk.Widget,
        title: str,
        variable: tk.StringVar,
        row: int,
        accent: str,
    ) -> None:
        card = tk.Frame(parent, bg=self.palette.panel, highlightthickness=1, highlightbackground=self.palette.panel_light)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        tk.Label(
            card,
            text=title.upper(),
            bg=self.palette.panel,
            fg=accent,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=18, pady=(14, 2))
        tk.Label(
            card,
            textvariable=variable,
            bg=self.palette.panel,
            fg=self.palette.text,
            justify="left",
            wraplength=390,
            font=("Segoe UI", 12),
        ).pack(anchor="w", fill="x", padx=18, pady=(0, 16))

    def _camera_card(self, parent: tk.Widget, row: int) -> None:
        card = tk.Frame(parent, bg=self.palette.panel, highlightthickness=1, highlightbackground=self.palette.panel_light)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        tk.Label(
            card,
            text="VISION OPENCV",
            bg=self.palette.panel,
            fg=self.palette.pink,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=18, pady=(14, 8))
        self.camera_canvas = tk.Canvas(card, width=390, height=220, bg="#050b13", highlightthickness=0)
        self.camera_canvas.pack(fill="x", padx=18)
        tk.Label(
            card,
            textvariable=self.face_text,
            bg=self.palette.panel,
            fg=self.palette.text,
            justify="left",
            wraplength=390,
            font=("Segoe UI", 10),
        ).pack(anchor="w", fill="x", padx=18, pady=(10, 16))

    def _draw_board(self) -> None:
        canvas = self.board_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 610)
        height = max(canvas.winfo_height(), 610)
        side = min(width, height) - 26
        left = (width - side) / 2
        top = (height - side) / 2
        cell = side / 3

        canvas.create_rectangle(left, top, left + side, top + side, fill=self.palette.panel, outline="")

        for index in range(9):
            row, col = divmod(index, 3)
            x1 = left + col * cell + 7
            y1 = top + row * cell + 7
            x2 = left + (col + 1) * cell - 7
            y2 = top + (row + 1) * cell - 7
            fill = self.palette.cell_hover if index == self.hover_cell and self._is_click_allowed(index) else self.palette.cell
            if index == self.last_move:
                fill = "#1c4a57"
            canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=self.palette.grid, width=2)

            mark = self.board[index]
            if mark == AI:
                self._draw_x(canvas, x1, y1, x2, y2)
            elif mark == HUMAN:
                self._draw_o(canvas, x1, y1, x2, y2)

        for i in (1, 2):
            x = left + i * cell
            y = top + i * cell
            canvas.create_line(x, top + 8, x, top + side - 8, fill=self.palette.cyan, width=3)
            canvas.create_line(left + 8, y, left + side - 8, y, fill=self.palette.cyan, width=3)

        line = winning_line(self.board)
        if line:
            centers = [self._cell_center(left, top, cell, pos) for pos in line]
            canvas.create_line(
                centers[0][0],
                centers[0][1],
                centers[-1][0],
                centers[-1][1],
                fill=self.palette.orange,
                width=9,
                capstyle="round",
            )

    def _draw_x(self, canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float) -> None:
        pad = 42
        canvas.create_line(x1 + pad, y1 + pad, x2 - pad, y2 - pad, fill=self.palette.pink, width=12, capstyle="round")
        canvas.create_line(x2 - pad, y1 + pad, x1 + pad, y2 - pad, fill=self.palette.pink, width=12, capstyle="round")

    def _draw_o(self, canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float) -> None:
        pad = 34
        canvas.create_oval(x1 + pad, y1 + pad, x2 - pad, y2 - pad, outline=self.palette.green, width=12)

    def _cell_center(self, left: float, top: float, cell: float, index: int) -> tuple[float, float]:
        row, col = divmod(index, 3)
        return left + col * cell + cell / 2, top + row * cell + cell / 2

    def _cell_at(self, event: tk.Event) -> int | None:
        width = max(self.board_canvas.winfo_width(), 610)
        height = max(self.board_canvas.winfo_height(), 610)
        side = min(width, height) - 26
        left = (width - side) / 2
        top = (height - side) / 2
        if not (left <= event.x <= left + side and top <= event.y <= top + side):
            return None
        col = min(2, int((event.x - left) // (side / 3)))
        row = min(2, int((event.y - top) // (side / 3)))
        return row * 3 + col

    def _on_board_motion(self, event: tk.Event) -> None:
        cell = self._cell_at(event)
        if cell != self.hover_cell:
            self.hover_cell = cell
            self._draw_board()

    def _on_board_leave(self, _event: tk.Event) -> None:
        self.hover_cell = None
        self._draw_board()

    def _on_board_click(self, event: tk.Event) -> None:
        index = self._cell_at(event)
        if index is None or not self._is_click_allowed(index):
            return

        self.board[index] = HUMAN
        self.last_move = index
        self.human_can_play = False
        self._draw_board()
        self._resolve_or_continue()

    def _is_click_allowed(self, index: int) -> bool:
        return (
            not self.game_over
            and self.current_player == HUMAN
            and self.human_can_play
            and self.board[index] == EMPTY
        )

    def _resolve_or_continue(self) -> None:
        state = winner(self.board)
        if state:
            self._finish_game(state)
            return
        self.current_player = AI
        self.turn_text.set("Turno IA: calculando jugada perfecta...")
        self.status_text.set("La IA esta explorando el arbol de decisiones.")
        self.after(450, self._ai_move)

    def _ai_move(self) -> None:
        if self.game_over:
            return

        self.last_result = best_move(self.board, AI, use_pruning=True)
        self.last_plain_result = best_move(self.board, AI, use_pruning=False)
        if self.last_result.position is not None:
            self.board[self.last_result.position] = AI
            self.last_move = self.last_result.position

        saved = self.last_plain_result.nodes - self.last_result.nodes
        self.metrics_text.set(
            f"Con poda: {self.last_result.nodes} nodos en {self.last_result.elapsed_ms:.2f} ms\n"
            f"Sin poda: {self.last_plain_result.nodes} nodos en {self.last_plain_result.elapsed_ms:.2f} ms\n"
            f"Ahorro: {saved} nodos | Puntaje: {self.last_result.score}"
        )
        self._draw_board()

        state = winner(self.board)
        if state:
            self._finish_game(state)
            return

        self.current_player = HUMAN
        self.turn_text.set("Turno humano: rostro requerido")
        self.status_text.set("Acercate a la camara; al detectar tu rostro se habilita el tablero.")

    def _finish_game(self, state: str) -> None:
        self.game_over = True
        self.human_can_play = False
        if state == AI:
            message = "Gano la IA. Minimax encontro una linea inevitable."
        elif state == HUMAN:
            message = "Gano el humano. Revisa el motor: esto no deberia ocurrir con juego optimo."
        else:
            message = "Empate perfecto. La IA se mantiene invencible."
        self.status_text.set(message)
        self.turn_text.set("Partida finalizada")
        self._draw_board()

    def _vision_loop(self) -> None:
        detection = self.detector.read()
        self.face_text.set(detection.message)

        if detection.frame is not None:
            self._render_camera(detection.frame, detection.faces)
        else:
            self._render_camera_placeholder(detection.message)

        if self.current_player == HUMAN and not self.game_over:
            self.human_can_play = detection.face_present
            if detection.face_present:
                self.status_text.set("Rostro detectado. Elige una casilla libre.")
                self.turn_text.set("Turno humano: tablero habilitado")
            else:
                self.turn_text.set("Turno humano: esperando rostro")
        else:
            self.human_can_play = False

        self._draw_board()
        self.after(170, self._vision_loop)

    def _render_camera(self, frame: object, faces: tuple[tuple[int, int, int, int], ...]) -> None:
        if Image is None or ImageTk is None or self.detector.cv2 is None:
            self._render_camera_placeholder("Instala Pillow para ver la camara dentro de la interfaz.")
            return

        cv2 = self.detector.cv2
        preview = frame.copy()
        for x, y, w, h in faces:
            cv2.rectangle(preview, (x, y), (x + w, y + h), (102, 242, 165), 3)
            cv2.putText(
                preview,
                "ROSTRO",
                (x, max(20, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (46, 230, 255),
                2,
            )
        rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb).resize((390, 220))
        self._camera_photo = ImageTk.PhotoImage(image)
        self.camera_canvas.delete("all")
        self.camera_canvas.create_image(0, 0, anchor="nw", image=self._camera_photo)

    def _render_camera_placeholder(self, message: str) -> None:
        self.camera_canvas.delete("all")
        self.camera_canvas.create_rectangle(0, 0, 390, 220, fill="#050b13", outline="")
        self.camera_canvas.create_text(
            195,
            110,
            text=message,
            fill=self.palette.muted,
            width=330,
            justify="center",
            font=("Segoe UI", 11, "bold"),
        )

    def _toggle_camera(self) -> None:
        self.detector.set_enabled(self.camera_enabled.get())

    def toggle_starter(self) -> None:
        self.ai_starts = not self.ai_starts
        self.reset_game()

    def reset_game(self) -> None:
        self.board = [EMPTY for _ in range(9)]
        self.game_over = False
        self.last_move = None
        self.hover_cell = None
        self.last_result = None
        self.last_plain_result = None
        self.metrics_text.set("La metrica aparecera despues del primer movimiento de IA.")
        if self.ai_starts:
            self.current_player = AI
            self.turn_text.set("La IA inicia: calculando primera jugada.")
            self.status_text.set("Nueva partida. La IA abre el juego.")
            self._draw_board()
            self.after(350, self._ai_move)
        else:
            self.current_player = HUMAN
            self.turn_text.set("Turno humano: rostro requerido")
            self.status_text.set("Nueva partida. Mira a la camara para activar tu turno.")
            self._draw_board()

    def _on_close(self) -> None:
        self.detector.stop()
        self.destroy()
