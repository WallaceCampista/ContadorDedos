"""Captura de vídeo com ciclo de vida garantido."""

from __future__ import annotations

import cv2


class CameraError(RuntimeError):
    """A câmera não pôde ser aberta ou parou de entregar frames."""


class Camera:
    """A webcam como *context manager*: valida ao abrir e libera ao sair.

    Frames inválidos são tolerados até ``max_failures`` seguidos — uma câmera
    real solta quadros vazios de vez em quando, mas uma sequência longa deles
    significa que ela sumiu.
    """

    #: Quantos frames inválidos seguidos toleramos antes de desistir.
    DEFAULT_MAX_FAILURES = 30

    def __init__(
        self,
        index: int = 0,
        mirror: bool = True,
        max_failures: int = DEFAULT_MAX_FAILURES,
    ) -> None:
        self.index = index
        self.mirror = mirror
        self.max_failures = max_failures
        self._capture: cv2.VideoCapture | None = None
        self._failures = 0

    def open(self) -> None:
        capture = cv2.VideoCapture(self.index)
        if not capture.isOpened():
            capture.release()
            raise CameraError(
                f"Não consegui abrir a câmera {self.index}. "
                "Verifique se ela está conectada, se outro programa não está usando-a "
                "e se o terminal tem permissão de acesso à câmera."
            )
        self._capture = capture
        self._failures = 0

    def read(self):
        """Devolve o próximo frame válido, já espelhado, ou ``None``.

        ``None`` significa "esse quadro veio vazio, tente de novo"; se isso se
        repetir ``max_failures`` vezes, levanta :class:`CameraError`.
        """
        if self._capture is None:
            raise CameraError("A câmera não foi aberta.")

        check, frame = self._capture.read()
        if not check or frame is None:
            self._failures += 1
            if self._failures >= self.max_failures:
                raise CameraError(f"A câmera {self.index} parou de entregar frames.")
            return None

        self._failures = 0
        return cv2.flip(frame, 1) if self.mirror else frame

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> Camera:
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()
