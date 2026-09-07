"""Recursos de visão compartilhados pela página web.

Streamlit reexecuta o script a cada interação, então detector e modelos precisam
viver **fora** desse ciclo — senão cada clique recarregaria o MediaPipe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2

from ..config import AppConfig
from ..core.pipeline import VideoClock
from ..modes import Mode, build_hand_tracker, build_modes
from ..modes.face_id import annotate_faces
from ..storage.faces_db import FaceDB
from ..ui.widgets import hud_scale
from ..vision.embedder import ARCFACE_FILENAME, ArcFaceEmbedder
from ..vision.faces import FACE_MODEL_FILENAME, FaceTracker


def mirror(image, mirrored: bool):
    """Espelha o frame, como o app nativo faz na captura."""
    return cv2.flip(image, 1) if mirrored else image


#: Rótulo do modo de rosto na barra lateral.
FACE_MODE_NAME = "Rosto (ID)"


@dataclass
class HandEngine:
    """Detector de mãos e os modos que o usam, criados uma vez por processo."""

    config: AppConfig
    tracker: object = field(init=False)
    modes: list[Mode] = field(init=False)
    clock: VideoClock = field(init=False)

    def __post_init__(self) -> None:
        self.tracker = build_hand_tracker(self.config)
        self.modes = [m for m in build_modes(self.config, self.tracker) if m.name != FACE_MODE_NAME]
        self.clock = VideoClock()

    def mode_names(self) -> list[str]:
        return [mode.name for mode in self.modes]

    def by_name(self, name: str) -> Mode | None:
        return next((mode for mode in self.modes if mode.name == name), None)

    def process(self, image, mode_name: str, mirrored: bool = True):
        """Anota um frame BGR com o modo escolhido. Devolve o frame anotado."""
        mode = self.by_name(mode_name)
        if mode is None:
            return image
        return mode.process(mirror(image, mirrored), self.clock.tick())


@dataclass
class FaceEngine:
    """Detector de rosto, embedder e a base local.

    O front web **reconhece e exclui**, mas não cadastra: o cadastro exige a tela
    de consentimento, e ela vive no app nativo. Manter uma única implementação do
    consentimento é mais seguro que duplicá-la em duas molduras.
    """

    config: AppConfig
    tracker: FaceTracker = field(init=False)
    embedder: ArcFaceEmbedder = field(init=False)
    clock: VideoClock = field(init=False)

    def __post_init__(self) -> None:
        models = self.config.models_dir
        self.tracker = FaceTracker(models / FACE_MODEL_FILENAME)
        self.embedder = ArcFaceEmbedder(models / ARCFACE_FILENAME)
        self.clock = VideoClock()

    def db(self) -> FaceDB:
        """Relê a base a cada uso: ela muda por fora (app nativo, exclusões)."""
        return FaceDB(self.config.faces_db)

    def process(self, image, db: FaceDB, threshold: float, mirrored: bool = True):
        """Reconhece e enquadra os rostos de um frame BGR."""
        image = mirror(image, mirrored)
        faces = self.tracker.detect(image, self.clock.tick())
        annotate_faces(image, faces, self.embedder, db, threshold, hud_scale(image.shape[0]))
        return image
