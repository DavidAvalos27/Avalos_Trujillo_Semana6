from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile


@dataclass(frozen=True)
class FaceDetection:
    camera_ready: bool
    face_present: bool
    frame: object | None
    faces: tuple[tuple[int, int, int, int], ...]
    message: str


class FaceDetector:
    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self.cv2 = None
        self.capture = None
        self.classifier = None
        self.error: str | None = None
        self.warning: str | None = None
        self.enabled = True
        self._load_opencv()

    def _load_opencv(self) -> None:
        try:
            import cv2

            self.cv2 = cv2
            cascade_path = self._prepare_cascade_path()
            self.classifier = cv2.CascadeClassifier(str(cascade_path))
            if self.classifier.empty():
                self.classifier = None
                self.warning = (
                    "Camara activa, pero no se pudo cargar el detector facial. "
                    "El tablero queda habilitado en modo respaldo."
                )
        except Exception as exc:  # pragma: no cover - depends on local install
            self.error = f"OpenCV no esta disponible: {exc}"

    def _prepare_cascade_path(self) -> Path:
        """Copy the cascade to an ASCII temp path for OpenCV on Windows.

        OpenCV's native file loader can fail with paths containing characters
        such as "°". Python can read those paths correctly, so we copy the XML
        once to the system temp directory and load it from there.
        """
        source = Path(self.cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        target_dir = Path(tempfile.gettempdir()) / "tres_en_raya_opencv"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name

        if source.exists() and (not target.exists() or source.stat().st_size != target.stat().st_size):
            shutil.copyfile(source, target)

        return target if target.exists() else source

    def start(self) -> None:
        if not self.enabled or self.cv2 is None or self.error:
            return
        if self.capture is not None and self.capture.isOpened():
            return
        self.capture = self.cv2.VideoCapture(self.camera_index)
        if not self.capture.isOpened():
            self.error = "No se pudo abrir la camara. Revisa permisos o conexion."
            self.capture.release()
            self.capture = None

    def stop(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if enabled:
            self.start()
        else:
            self.stop()

    def read(self) -> FaceDetection:
        if not self.enabled:
            return FaceDetection(False, True, None, (), "Camara desactivada: turno manual.")
        if self.error:
            return FaceDetection(False, False, None, (), self.error)

        self.start()
        if self.capture is None:
            return FaceDetection(False, False, None, (), "Camara no disponible.")

        ok, frame = self.capture.read()
        if not ok:
            return FaceDetection(False, False, None, (), "No se pudo leer imagen de la camara.")

        if self.classifier is None:
            message = self.warning or "Detector facial no disponible. Modo respaldo activo."
            return FaceDetection(True, True, frame, (), message)

        gray = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY)
        gray = self.cv2.equalizeHist(gray)
        detected = self.classifier.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=5,
            minSize=(70, 70),
        )
        faces = tuple((int(x), int(y), int(w), int(h)) for x, y, w, h in detected)
        message = "Rostro detectado: puedes jugar." if faces else "Esperando rostro para habilitar tu turno."
        return FaceDetection(True, bool(faces), frame, faces, message)
