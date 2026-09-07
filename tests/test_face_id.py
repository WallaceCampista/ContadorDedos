"""Testes do modo Rosto (ID): consentimento, cadastro e exclusão.

Detector e embedder são substituídos por dublês — o fluxo é exercitado inteiro
sem câmera, sem modelo e sem rede.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from contador_dedos.modes.face_id import (
    CONSENT_LINES,
    ENROLL_FRAMES,
    UNKNOWN_NAME,
    FaceId,
    Stage,
)
from contador_dedos.storage.faces_db import FaceDB
from contador_dedos.vision.faces import DetectedFace
from contador_dedos.vision.model import ModelError

DIM = 8


class FakeTracker:
    """Detector de mentira: devolve os rostos que o teste mandar."""

    def __init__(self, faces=None):
        self.faces = (
            faces
            if faces is not None
            else [
                DetectedFace(
                    box=(10, 10, 60, 60),
                    keypoints=[(20, 30), (50, 30), (35, 40), (35, 55)],
                    score=0.9,
                )
            ]
        )
        self.fechado = False

    def detect(self, frame, timestamp_ms):
        return self.faces

    def close(self):
        self.fechado = True


class FakeEmbedder:
    """Devolve sempre o mesmo vetor, para o reconhecimento ser determinístico."""

    dimension = DIM

    def __init__(self, eixo: int = 0):
        self.eixo = eixo

    def embed(self, aligned_face):
        v = np.zeros(DIM, dtype=np.float32)
        v[self.eixo] = 1.0
        return v


def frame(width: int = 640, height: int = 480) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def build(tmp_path, tracker=None, embedder=None, **kwargs) -> FaceId:
    modo = FaceId(
        db=FaceDB(tmp_path / "faces.npz", dimension=DIM),
        tracker_factory=lambda: tracker or FakeTracker(),
        embedder_factory=lambda: embedder or FakeEmbedder(),
        **kwargs,
    )
    # Dois frames: o primeiro só avisa, o segundo constrói os recursos.
    modo.process(frame())
    modo.process(frame())
    return modo


@pytest.fixture
def modo(tmp_path) -> FaceId:
    return build(tmp_path)


def rodar(modo, n=1):
    for _ in range(n):
        saida = modo.process(frame())
    return saida


# --- preparação tardia ------------------------------------------------------


def test_avisa_antes_de_bloquear_no_download(tmp_path):
    """O usuário precisa ver a mensagem antes do download travar a janela."""
    modo = FaceId(
        db=FaceDB(tmp_path / "faces.npz", dimension=DIM),
        tracker_factory=FakeTracker,
        embedder_factory=FakeEmbedder,
    )
    assert modo.ready is False
    modo.process(frame())
    assert modo.ready is False, "o primeiro frame só avisa"
    modo.process(frame())
    assert modo.ready is True


def test_falha_ao_preparar_nao_derruba_o_app(tmp_path):
    def explode():
        raise ModelError("sem rede")

    modo = FaceId(
        db=FaceDB(tmp_path / "faces.npz", dimension=DIM),
        tracker_factory=explode,
        embedder_factory=FakeEmbedder,
    )
    rodar(modo, 3)
    assert modo._error == "sem rede"
    assert rodar(modo) is not None, "o modo continua desenhando algo"


# --- consentimento ----------------------------------------------------------


def test_comeca_reconhecendo(modo):
    assert modo.stage is Stage.RECOGNIZING


def test_cadastrar_passa_obrigatoriamente_pelo_consentimento(modo):
    modo._pending = "enroll"
    rodar(modo)
    assert modo.stage is Stage.CONSENT, "não se cadastra sem passar pelo aviso"


def test_consentimento_recusado_volta_sem_cadastrar(modo):
    modo._pending = "enroll"
    rodar(modo)
    modo._pending = "cancel"
    rodar(modo)
    assert modo.stage is Stage.RECOGNIZING
    assert modo.db.names() == []


def test_texto_de_consentimento_cobre_o_exigido():
    """A Seção 5.5 pede: o que, onde e como excluir."""
    texto = " ".join(CONSENT_LINES).lower()
    assert "lgpd" in texto
    assert "sensível" in texto
    assert "embedding" in texto and "foto" in texto
    assert "internet" in texto
    assert "excluir" in texto


# --- cadastro ---------------------------------------------------------------


def aceitar_e_nomear(modo, nome: str):
    modo._pending = "enroll"
    rodar(modo)
    modo._pending = "accept"
    rodar(modo)
    for letra in nome:
        modo.on_key(ord(letra))
    modo._pending = "confirm-name"
    rodar(modo)


def test_fluxo_completo_de_cadastro(modo):
    aceitar_e_nomear(modo, "Ana")
    assert modo.stage is Stage.CAPTURING
    rodar(modo, ENROLL_FRAMES)
    assert modo.stage is Stage.RECOGNIZING
    assert modo.db.names() == ["Ana"]


def test_nome_vazio_nao_avanca(modo):
    modo._pending = "enroll"
    rodar(modo)
    modo._pending = "accept"
    rodar(modo)
    modo._pending = "confirm-name"
    rodar(modo)
    assert modo.stage is Stage.NAMING
    assert modo._message is not None


def test_digitacao_consome_as_teclas(modo):
    modo._pending = "enroll"
    rodar(modo)
    modo._pending = "accept"
    rodar(modo)
    assert modo.on_key(ord("q")) is True, "'q' digitado não pode encerrar o app"
    assert modo._typed == "q"
    assert modo.on_key(8) is True
    assert modo._typed == ""


def test_teclas_so_sao_consumidas_ao_digitar(modo):
    assert modo.on_key(ord("q")) is False


def test_esc_cancela_o_cadastro_sem_sair_do_modo(modo):
    modo._pending = "enroll"
    rodar(modo)
    modo._pending = "accept"
    rodar(modo)
    assert modo.on_key(27) is True
    rodar(modo)
    assert modo.stage is Stage.RECOGNIZING
    assert modo.db.names() == []


def test_cadastro_exige_um_rosto_por_vez(tmp_path):
    dois = FakeTracker(
        [
            DetectedFace(
                box=(0, 0, 30, 30), keypoints=[(5, 8), (20, 8), (12, 14), (12, 22)], score=0.9
            ),
            DetectedFace(
                box=(40, 0, 30, 30), keypoints=[(45, 8), (60, 8), (52, 14), (52, 22)], score=0.9
            ),
        ]
    )
    modo = build(tmp_path, tracker=dois)
    aceitar_e_nomear(modo, "Ana")
    rodar(modo, ENROLL_FRAMES * 2)
    assert modo.stage is Stage.CAPTURING, "com dois rostos, não captura"
    assert modo.db.names() == []


# --- reconhecimento ---------------------------------------------------------


def test_reconhece_quem_foi_cadastrado(modo):
    aceitar_e_nomear(modo, "Ana")
    rodar(modo, ENROLL_FRAMES)
    nome, _ = modo.db.match(FakeEmbedder().embed(None), modo.threshold)
    assert nome == "Ana"


def test_rosto_diferente_fica_desconhecido(tmp_path):
    modo = build(tmp_path, embedder=FakeEmbedder(eixo=0))
    aceitar_e_nomear(modo, "Ana")
    rodar(modo, ENROLL_FRAMES)
    outro = FakeEmbedder(eixo=1).embed(None)
    assert modo.db.match(outro, modo.threshold)[0] is None
    assert UNKNOWN_NAME == "Desconhecido"


def test_sem_rosto_no_quadro_mostra_estado_vazio(tmp_path):
    modo = build(tmp_path, tracker=FakeTracker([]))
    img = rodar(modo)
    meio = img[img.shape[0] // 3 : 2 * img.shape[0] // 3]
    assert meio.any(), "faltou a mensagem de estado vazio"


# --- exclusão ---------------------------------------------------------------


def test_gerenciar_lista_e_exclui(modo):
    aceitar_e_nomear(modo, "Ana")
    rodar(modo, ENROLL_FRAMES)
    modo._pending = "manage"
    rodar(modo)
    assert modo.stage is Stage.MANAGING
    modo._pending = "delete:Ana"
    rodar(modo)
    assert modo.db.names() == []
    assert "Ana" in modo._message


def test_botao_de_exclusao_aparece_para_cada_cadastro(modo):
    aceitar_e_nomear(modo, "Ana")
    rodar(modo, ENROLL_FRAMES)
    modo._pending = "manage"
    rodar(modo)
    acoes = {acao for _, acao in modo._buttons}
    assert "delete:Ana" in acoes, "sem botão, não há direito ao esquecimento"
    assert "back" in acoes


def test_clique_aciona_o_botao_sob_o_cursor(modo):
    rodar(modo)
    rect, acao = modo._buttons[0]
    modo.on_mouse(cv2.EVENT_LBUTTONDOWN, *rect.center)
    assert modo._pending == acao


def test_mouse_fora_dos_botoes_nao_aciona_nada(modo):
    rodar(modo)
    modo.on_mouse(cv2.EVENT_LBUTTONDOWN, 1, 1)
    assert modo._pending is None


# --- recursos ---------------------------------------------------------------


def test_close_libera_o_detector(tmp_path):
    tracker = FakeTracker()
    modo = build(tmp_path, tracker=tracker)
    modo.close()
    assert tracker.fechado is True


def test_close_e_seguro_sem_preparacao(tmp_path):
    modo = FaceId(
        db=FaceDB(tmp_path / "faces.npz", dimension=DIM),
        tracker_factory=FakeTracker,
        embedder_factory=FakeEmbedder,
    )
    modo.close()  # não pode estourar
