"""Integração do stack facial real, sobre uma foto de verdade.

Estes testes usam os modelos de fato (detector + ArcFace) e por isso são
**pulados** quando eles não estão em disco — a CI não baixa ~122 MB. Rode
localmente depois de abrir o modo Rosto uma vez.

A foto é a `grace_hopper.jpg` que vem dentro do matplotlib: uma imagem já
instalada, para o teste não depender de rede nem da webcam.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from contador_dedos.config import DEFAULT_MODEL_PATH
from contador_dedos.storage.faces_db import FaceDB
from contador_dedos.vision.embedder import (
    ARCFACE_FILENAME,
    DEFAULT_THRESHOLD,
    ArcFaceEmbedder,
    cosine_distance,
)
from contador_dedos.vision.faces import FACE_MODEL_FILENAME, FaceTracker, align_face

MODELS = DEFAULT_MODEL_PATH.parent
FACE_MODEL = MODELS / FACE_MODEL_FILENAME
ARCFACE_MODEL = MODELS / ARCFACE_FILENAME


def _foto_de_teste() -> Path | None:
    try:
        import matplotlib
    except ImportError:
        return None
    caminho = Path(matplotlib.__file__).parent / "mpl-data/sample_data/grace_hopper.jpg"
    return caminho if caminho.is_file() else None


FOTO = _foto_de_teste()

pytestmark = [
    pytest.mark.skipif(
        not (FACE_MODEL.is_file() and ARCFACE_MODEL.is_file()),
        reason="modelos faciais ausentes (abra o modo Rosto uma vez para baixá-los)",
    ),
    pytest.mark.skipif(FOTO is None, reason="foto de teste indisponível"),
]


@pytest.fixture(scope="module")
def tracker():
    with FaceTracker(FACE_MODEL) as t:
        yield t


@pytest.fixture(scope="module")
def embedder():
    return ArcFaceEmbedder(ARCFACE_MODEL)


@pytest.fixture(scope="module")
def foto() -> np.ndarray:
    return cv2.imread(str(FOTO))


def _embedding(tracker, embedder, imagem, timestamp: int):
    faces = tracker.detect(imagem, timestamp)
    if not faces:
        return None
    alinhado = align_face(imagem, faces[0])
    return None if alinhado is None else embedder.embed(alinhado)


def test_detecta_o_rosto_na_foto(tracker, foto):
    faces = tracker.detect(foto, 0)
    assert len(faces) == 1
    assert faces[0].score > 0.8
    assert len(faces[0].keypoints) == 6


def test_embedding_tem_dimensao_e_norma_esperadas(tracker, embedder, foto):
    emb = _embedding(tracker, embedder, foto, 10)
    assert emb is not None
    assert emb.shape == (embedder.dimension,)
    assert np.linalg.norm(emb) == pytest.approx(1.0, abs=1e-5)


def test_mesma_pessoa_sob_brilho_e_rotacao_continua_perto(tracker, embedder, foto):
    """O que o limiar precisa tolerar: a mesma pessoa em condições diferentes."""
    altura, largura = foto.shape[:2]
    matriz = cv2.getRotationMatrix2D((largura / 2, altura / 2), 8, 1.0)
    variante = cv2.warpAffine(
        cv2.convertScaleAbs(foto, alpha=1.25, beta=25), matriz, (largura, altura)
    )
    original = _embedding(tracker, embedder, foto, 20)
    alterada = _embedding(tracker, embedder, variante, 30)
    assert alterada is not None, "o detector perdeu o rosto na variante"
    assert cosine_distance(original, alterada) < DEFAULT_THRESHOLD


def test_imagem_sem_rosto_fica_longe(tracker, embedder, foto):
    """E o que ele precisa rejeitar."""
    ruido = np.random.RandomState(0).randint(0, 255, (112, 112, 3), dtype=np.uint8)
    original = _embedding(tracker, embedder, foto, 40)
    assert cosine_distance(original, embedder.embed(ruido)) > DEFAULT_THRESHOLD


def test_cadastro_e_reconhecimento_de_ponta_a_ponta(tracker, embedder, foto, tmp_path):
    db = FaceDB(tmp_path / "faces.npz", dimension=embedder.dimension)
    emb = _embedding(tracker, embedder, foto, 50)
    db.add("Grace", emb)
    assert db.match(emb, DEFAULT_THRESHOLD)[0] == "Grace"

    ruido = np.random.RandomState(1).randint(0, 255, (112, 112, 3), dtype=np.uint8)
    assert db.match(embedder.embed(ruido), DEFAULT_THRESHOLD)[0] is None

    assert db.delete("Grace") is True
    assert db.match(emb, DEFAULT_THRESHOLD)[0] is None
