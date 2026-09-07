"""Testes do alinhamento facial, do embedder e do download em pacote zip."""

from __future__ import annotations

import hashlib
import io
import zipfile

import numpy as np
import pytest

from contador_dedos.vision import model as model_module
from contador_dedos.vision.embedder import cosine_distance, normalize
from contador_dedos.vision.faces import (
    ALIGNED_SIZE,
    FACE_MODEL_SHA256,
    FACE_MODEL_URL,
    DetectedFace,
    align_face,
)
from contador_dedos.vision.model import ModelError, ensure_model_from_archive


def frame(width: int = 320, height: int = 240) -> np.ndarray:
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[60:180, 80:240] = 200  # um "rosto" claro no meio
    return img


def rosto(inclinado: bool = False) -> DetectedFace:
    olhos = [(120, 100), (200, 140)] if inclinado else [(120, 100), (200, 100)]
    return DetectedFace(
        box=(80, 60, 160, 120), keypoints=[*olhos, (160, 130), (160, 160)], score=0.9
    )


# --- alinhamento ------------------------------------------------------------


def test_alinhamento_devolve_o_tamanho_do_arcface():
    saida = align_face(frame(), rosto())
    assert saida.shape == (ALIGNED_SIZE, ALIGNED_SIZE, 3)


def test_alinhamento_endireita_um_rosto_inclinado():
    """É o ponto do alinhamento: a mesma pessoa torta não pode virar outra."""
    reto = align_face(frame(), rosto())
    torto = align_face(frame(), rosto(inclinado=True))
    assert reto is not None and torto is not None
    assert reto.shape == torto.shape


def test_alinhamento_independe_de_qual_olho_vem_primeiro():
    """Ordenar os olhos por X torna o recorte imune à convenção do MediaPipe."""
    face = rosto()
    trocado = DetectedFace(
        box=face.box,
        keypoints=[face.keypoints[1], face.keypoints[0], *face.keypoints[2:]],
        score=face.score,
    )
    assert np.array_equal(align_face(frame(), face), align_face(frame(), trocado))


def test_sem_keypoints_nao_ha_alinhamento():
    sem = DetectedFace(box=(10, 10, 40, 40), keypoints=[], score=0.5)
    assert align_face(frame(), sem) is None


def test_caixa_fora_do_frame_nao_quebra():
    fora = DetectedFace(box=(500, 500, 40, 40), keypoints=[(1, 1), (2, 2)], score=0.5)
    assert align_face(frame(), fora) is None


def test_centro_da_caixa():
    assert rosto().center == (160, 120)


# --- distância --------------------------------------------------------------


def test_normalize_deixa_norma_unitaria():
    assert np.linalg.norm(normalize(np.array([3.0, 4.0]))) == pytest.approx(1.0)


def test_normalize_aguenta_vetor_nulo():
    assert not np.isnan(normalize(np.zeros(4))).any()


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [([1, 0], [1, 0], 0.0), ([1, 0], [0, 1], 1.0), ([1, 0], [-1, 0], 2.0)],
)
def test_distancia_de_cosseno(a, b, esperado):
    va, vb = normalize(np.array(a, dtype=float)), normalize(np.array(b, dtype=float))
    assert cosine_distance(va, vb) == pytest.approx(esperado)


# --- modelo dentro de zip ---------------------------------------------------

CONTEUDO = b"modelo-falso" * 100
MEMBRO = "w600k_mbf.onnx"


def zip_com(nome: str, dados: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(nome, dados)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, data: bytes):
        self._data, self._pos = data, 0
        self.headers = {"Content-Length": str(len(data))}

    def read(self, size):
        chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture
def servindo(monkeypatch):
    def _servir(payload: bytes):
        monkeypatch.setattr(
            model_module.urllib.request, "urlopen", lambda *a, **k: FakeResponse(payload)
        )

    return _servir


def test_extrai_apenas_o_modelo_do_pacote(tmp_path, servindo):
    """Baixa ~122 MB uma vez, mas guarda só os ~14 MB que interessam."""
    pacote = zip_com(MEMBRO, CONTEUDO)
    servindo(pacote)
    destino = tmp_path / "arcface.onnx"
    ensure_model_from_archive(
        destino,
        "https://exemplo.invalido/buffalo.zip",
        hashlib.sha256(pacote).hexdigest(),
        MEMBRO,
        hashlib.sha256(CONTEUDO).hexdigest(),
    )
    assert destino.read_bytes() == CONTEUDO
    assert list(tmp_path.glob("*.zip")) == [], "o pacote precisa ser descartado"
    assert list(tmp_path.glob("*.part")) == []


def test_modelo_ausente_no_pacote_avisa(tmp_path, servindo):
    pacote = zip_com("outro.onnx", CONTEUDO)
    servindo(pacote)
    with pytest.raises(ModelError, match="não contém"):
        ensure_model_from_archive(
            tmp_path / "arcface.onnx",
            "https://exemplo.invalido/buffalo.zip",
            hashlib.sha256(pacote).hexdigest(),
            MEMBRO,
            hashlib.sha256(CONTEUDO).hexdigest(),
        )


def test_modelo_com_hash_errado_e_recusado(tmp_path, servindo):
    pacote = zip_com(MEMBRO, CONTEUDO)
    servindo(pacote)
    destino = tmp_path / "arcface.onnx"
    with pytest.raises(ModelError, match="hash esperado"):
        ensure_model_from_archive(
            destino,
            "https://exemplo.invalido/buffalo.zip",
            hashlib.sha256(pacote).hexdigest(),
            MEMBRO,
            "0" * 64,
        )
    assert not destino.exists()


def test_modelo_ja_em_disco_nao_baixa_nada(tmp_path):
    destino = tmp_path / "arcface.onnx"
    destino.write_bytes(CONTEUDO)
    assert ensure_model_from_archive(destino, "url", "x", MEMBRO, "y") == destino


def test_constantes_do_detector_de_rosto():
    assert FACE_MODEL_URL.endswith(".tflite")
    assert "/1/" in FACE_MODEL_URL, "a URL precisa apontar para uma versão fixa"
    assert len(FACE_MODEL_SHA256) == 64
