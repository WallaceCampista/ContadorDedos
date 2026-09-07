"""Snapshots e gravação de vídeo do que está na tela."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import cv2

#: Prefixo dos arquivos gerados.
PREFIX = "contador-dedos"
#: Codec do vídeo. `mp4v` é o que vem em qualquer build do OpenCV.
FOURCC = "mp4v"
DEFAULT_FPS = 20.0


class RecorderError(RuntimeError):
    """O vídeo não pôde ser aberto para gravação."""


def timestamped_name(extension: str, now: datetime | None = None) -> str:
    """Nome de arquivo com data e hora, para não sobrescrever nada."""
    momento = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"{PREFIX}_{momento}.{extension}"


class Recorder:
    """Salva PNGs e grava MP4 do frame já anotado.

    A gravação é do frame *como o usuário o vê* — com landmarks, contadores e
    barra de status —, exceto o indicador de REC, que o `App` desenha depois de
    entregar o frame aqui.
    """

    def __init__(self, output_dir: Path, fps: float = DEFAULT_FPS) -> None:
        self.output_dir = Path(output_dir)
        self.fps = fps
        self._writer: cv2.VideoWriter | None = None
        self._path: Path | None = None
        self._started_at = 0.0

    @property
    def is_recording(self) -> bool:
        return self._writer is not None

    @property
    def elapsed(self) -> float:
        """Segundos desde o início da gravação."""
        return time.monotonic() - self._started_at if self.is_recording else 0.0

    def snapshot(self, frame) -> Path:
        """Salva o frame atual como PNG e devolve o caminho."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        destino = self.output_dir / timestamped_name("png")
        if not cv2.imwrite(str(destino), frame):
            raise RecorderError(f"Não consegui salvar {destino}.")
        return destino

    def start(self, frame) -> Path:
        """Começa a gravar, no tamanho do frame recebido."""
        if self.is_recording:
            return self._path
        self.output_dir.mkdir(parents=True, exist_ok=True)
        destino = self.output_dir / timestamped_name("mp4")
        height, width = frame.shape[:2]
        writer = cv2.VideoWriter(
            str(destino), cv2.VideoWriter_fourcc(*FOURCC), self.fps, (width, height)
        )
        if not writer.isOpened():
            writer.release()
            raise RecorderError(f"Não consegui abrir {destino} para gravação.")
        self._writer, self._path, self._started_at = writer, destino, time.monotonic()
        return destino

    def write(self, frame) -> None:
        """Acrescenta um frame à gravação em curso. Sem gravação, não faz nada."""
        if self._writer is not None:
            self._writer.write(frame)

    def stop(self) -> Path | None:
        """Encerra a gravação e devolve o arquivo gerado."""
        if self._writer is None:
            return None
        self._writer.release()
        caminho, self._writer, self._path = self._path, None, None
        return caminho

    def toggle(self, frame) -> Path:
        """Liga ou desliga a gravação. Devolve o arquivo envolvido."""
        return self.stop() if self.is_recording else self.start(frame)

    def close(self) -> None:
        self.stop()
