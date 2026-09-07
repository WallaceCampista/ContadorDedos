"""Wrapper do detector de mãos do MediaPipe.

Isola a Tasks API (`HandLandmarker`) do resto do projeto: trocar ou atualizar o
MediaPipe mexe só neste arquivo. Foi exatamente essa fronteira que faltou quando
a API legada `mp.solutions` desapareceu na versão 0.10.35.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
)

from .model import ensure_model

#: Modelo da Tasks API. A URL é versionada, então o hash é estável.
HAND_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
HAND_MODEL_SHA256 = "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1"


def ensure_hand_model(model_path: Path) -> Path:
    """Garante o modelo de mãos em disco, baixando-o se faltar.

    É o ponto único usado pelo `setup.sh` e pelo :class:`HandTracker`, para que
    a URL e o hash tenham um só dono.
    """
    return ensure_model(model_path, HAND_MODEL_URL, HAND_MODEL_SHA256)


@dataclass(frozen=True)
class DetectedHand:
    """Uma mão detectada em um frame.

    Attributes:
        landmarks: os 21 landmarks normalizados, como o MediaPipe os devolve.
        handedness: ``"Left"`` ou ``"Right"``, no referencial do frame
            processado — ver :func:`real_hand`.
        score: confiança da classificação de lateralidade.
    """

    landmarks: list
    handedness: str
    score: float


def real_hand(handedness: str, mirrored: bool) -> str:
    """Converte o rótulo do MediaPipe na mão real da pessoa.

    O MediaPipe assume imagem espelhada: com ``cv2.flip`` aplicado o rótulo já
    corresponde à mão real; sem espelhamento, ele vem trocado.
    """
    if mirrored:
        return handedness
    return "Left" if handedness == "Right" else "Right"


class HandTracker:
    """Detecta mãos em uma sequência de vídeo.

    É um *context manager*: o modelo é liberado ao sair do bloco.
    """

    def __init__(
        self,
        model_path: Path,
        max_hands: int = 2,
        detection_confidence: float = 0.5,
        tracking_confidence: float = 0.5,
    ) -> None:
        ensure_hand_model(model_path)
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._landmarker = HandLandmarker.create_from_options(options)

    def detect(self, frame, timestamp_ms: int) -> list[DetectedHand]:
        """Detecta as mãos em um frame BGR.

        ``timestamp_ms`` precisa crescer estritamente entre chamadas — é o que
        :class:`~contador_dedos.core.pipeline.VideoClock` garante.
        """
        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
        )
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        return [
            DetectedHand(
                landmarks=landmarks,
                handedness=handedness[0].category_name,
                score=handedness[0].score,
            )
            for landmarks, handedness in zip(result.hand_landmarks, result.handedness)
        ]

    def close(self) -> None:
        self._landmarker.close()

    def __enter__(self) -> HandTracker:
        return self

    def __exit__(self, *_) -> None:
        self.close()
