"""Detecção e alinhamento de rostos, via MediaPipe Face Detector.

Fica na mesma camada do detector de mãos, pelo mesmo motivo: trocar a biblioteca
de visão deve mexer só aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceDetector,
    FaceDetectorOptions,
    RunningMode,
)

from .landmarks import Point
from .model import ensure_model

#: BlazeFace de curto alcance — 224 KB, para rostos a até ~2 m da câmera.
FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_detector/"
    "blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
)
FACE_MODEL_SHA256 = "b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f"
FACE_MODEL_FILENAME = "blaze_face_short_range.tflite"

#: Lado do recorte que o ArcFace espera.
ALIGNED_SIZE = 112

#: Índices dos keypoints do BlazeFace usados no alinhamento.
_EYE_A, _EYE_B, _MOUTH = 0, 1, 3

#: Gabarito do ArcFace em 112x112: olho da esquerda da imagem, olho da direita e
#: centro da boca (média dos dois cantos do gabarito original de 5 pontos).
_TEMPLATE = np.array([[38.2946, 51.6963], [73.5318, 51.5014], [56.1396, 92.2848]], dtype=np.float32)


@dataclass(frozen=True)
class DetectedFace:
    """Um rosto detectado em um frame.

    Attributes:
        box: ``(x, y, largura, altura)`` em pixels.
        keypoints: os 6 pontos do BlazeFace, em pixels.
        score: confiança da detecção.
    """

    box: tuple[int, int, int, int]
    keypoints: list[Point]
    score: float

    @property
    def center(self) -> Point:
        x, y, width, height = self.box
        return x + width // 2, y + height // 2


def ensure_face_model(model_path: Path) -> Path:
    """Garante o modelo de detecção de rosto em disco, baixando-o se faltar."""
    return ensure_model(model_path, FACE_MODEL_URL, FACE_MODEL_SHA256)


def align_face(frame, face: DetectedFace) -> np.ndarray | None:
    """Recorta e alinha o rosto em 112x112, como o ArcFace espera.

    Usa uma transformação de similaridade dos olhos e da boca para o gabarito
    do ArcFace: sem esse alinhamento, uma cabeça inclinada gera um embedding
    bem diferente do mesmo rosto na vertical.

    Devolve ``None`` se o rosto não tiver keypoints utilizáveis.
    """
    if len(face.keypoints) <= _MOUTH:
        return None

    # Ordenar os olhos por X torna o alinhamento imune à convenção de qual é o
    # olho "direito" — o que importa é qual aparece à esquerda da imagem.
    eyes = sorted((face.keypoints[_EYE_A], face.keypoints[_EYE_B]), key=lambda p: p[0])
    origem = np.array([*eyes, face.keypoints[_MOUTH]], dtype=np.float32)

    matrix, _ = cv2.estimateAffinePartial2D(origem, _TEMPLATE, method=cv2.LMEDS)
    if matrix is None:
        return _crop_box(frame, face)
    return cv2.warpAffine(frame, matrix, (ALIGNED_SIZE, ALIGNED_SIZE), flags=cv2.INTER_LINEAR)


def _crop_box(frame, face: DetectedFace) -> np.ndarray | None:
    """Recorte simples da caixa — o plano B quando o alinhamento não converge."""
    height, width = frame.shape[:2]
    x, y, box_width, box_height = face.box
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + box_width, width), min(y + box_height, height)
    if x1 <= x0 or y1 <= y0:
        return None
    return cv2.resize(frame[y0:y1, x0:x1], (ALIGNED_SIZE, ALIGNED_SIZE))


class FaceTracker:
    """Detecta rostos em uma sequência de vídeo. É um *context manager*."""

    def __init__(self, model_path: Path, min_confidence: float = 0.5) -> None:
        ensure_face_model(model_path)
        options = FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.VIDEO,
            min_detection_confidence=min_confidence,
        )
        self._detector = FaceDetector.create_from_options(options)

    def detect(self, frame, timestamp_ms: int) -> list[DetectedFace]:
        """Detecta os rostos em um frame BGR."""
        height, width = frame.shape[:2]
        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
        )
        result = self._detector.detect_for_video(image, timestamp_ms)
        return [
            DetectedFace(
                box=(
                    detection.bounding_box.origin_x,
                    detection.bounding_box.origin_y,
                    detection.bounding_box.width,
                    detection.bounding_box.height,
                ),
                keypoints=[
                    (int(point.x * width), int(point.y * height))
                    for point in (detection.keypoints or [])
                ],
                score=detection.categories[0].score if detection.categories else 0.0,
            )
            for detection in result.detections
        ]

    def close(self) -> None:
        self._detector.close()

    def __enter__(self) -> FaceTracker:
        return self

    def __exit__(self, *_) -> None:
        self.close()
