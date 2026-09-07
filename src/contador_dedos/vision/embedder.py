"""Embedding facial: transforma um rosto alinhado em um vetor de identidade.

A interface :class:`Embedder` é o ponto de troca previsto na Seção 5.4 do plano
— a implementação atual é o ArcFace (MobileFaceNet, 512-d) rodando em
`onnxruntime`, mas nada fora deste arquivo depende dessa escolha.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from .model import ensure_model_from_archive

#: O modelo vem no pacote `buffalo_s` publicado pelo próprio InsightFace.
ARCFACE_ARCHIVE_URL = (
    "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip"
)
ARCFACE_ARCHIVE_SHA256 = "d85a87f503f691807cd8bb97128bdf7a0660326cd9cd02657127fa978bab8b5e"
ARCFACE_MEMBER = "w600k_mbf.onnx"
ARCFACE_SHA256 = "9cc6e4a75f0e2bf0b1aed94578f144d15175f357bdc05e815e5c4a02b319eb4f"
ARCFACE_FILENAME = "arcface_w600k_mbf.onnx"

#: Distância de cosseno acima da qual dois rostos são considerados pessoas
#: diferentes. É um ponto de partida — ajuste com `--face-threshold`: menor
#: significa mais rigor (menos falsos positivos, mais "Desconhecido").
DEFAULT_THRESHOLD = 0.62

#: Normalização que o ArcFace espera: canais RGB, valores em [-1, 1].
_SCALE = 1.0 / 127.5
_MEAN = (127.5, 127.5, 127.5)


class Embedder(Protocol):
    """Converte um rosto alinhado em um vetor de identidade normalizado."""

    dimension: int

    def embed(self, aligned_face: np.ndarray) -> np.ndarray:
        """Recebe um recorte BGR alinhado e devolve o vetor, com norma 1."""


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Distância de cosseno entre dois vetores já normalizados: 0 = idênticos."""
    return float(1.0 - np.dot(a, b))


def normalize(vector: np.ndarray) -> np.ndarray:
    """Deixa o vetor com norma 1, para a distância de cosseno virar um produto."""
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector.astype(np.float32)
    return (vector / norm).astype(np.float32)


class ArcFaceEmbedder:
    """ArcFace (MobileFaceNet, 512-d) sobre `onnxruntime`."""

    dimension = 512

    def __init__(self, model_path: Path) -> None:
        import onnxruntime  # importado aqui: só o modo de rosto paga esse custo

        ensure_model_from_archive(
            model_path,
            ARCFACE_ARCHIVE_URL,
            ARCFACE_ARCHIVE_SHA256,
            ARCFACE_MEMBER,
            ARCFACE_SHA256,
        )
        self._session = onnxruntime.InferenceSession(
            str(model_path), providers=["CPUExecutionProvider"]
        )
        self._input = self._session.get_inputs()[0].name

    def embed(self, aligned_face: np.ndarray) -> np.ndarray:
        blob = cv2.dnn.blobFromImage(
            aligned_face, _SCALE, aligned_face.shape[1::-1], _MEAN, swapRB=True
        )
        vector = self._session.run(None, {self._input: blob})[0][0]
        return normalize(vector)
