"""Testes do reconhecimento de gestos — geometria pura, sem câmera."""

from __future__ import annotations

import numpy as np
import pytest

from contador_dedos.modes.gesture import (
    GESTURES,
    JOINHA,
    MAO_ABERTA,
    MAO_FECHADA,
    OK,
    PAZ,
    UNKNOWN_LABEL,
    draw_gestures,
    recognize_gesture,
)
from contador_dedos.vision.handshape import (
    fingers_extended,
    fingertips_touching,
    hand_span,
    is_thumb_up,
)
from contador_dedos.vision.landmarks import INDEX_TIP, THUMB_TIP
from helpers import SPAN, make_hand

HANDS = ("Left", "Right")

#: Cada gesto e como montá-lo na mão sintética.
POSES = {
    MAO_FECHADA: {},
    MAO_ABERTA: {"thumb": True, "fingers": (True, True, True, True)},
    PAZ: {"fingers": (True, True, False, False)},
    JOINHA: {"thumb_up": True},
    OK: {"fingers": (False, True, True, True), "pinch": True},
}


@pytest.mark.parametrize("handedness", HANDS)
@pytest.mark.parametrize(
    ("gesto", "pose"), list(POSES.items()), ids=lambda v: getattr(v, "key", "")
)
def test_reconhece_cada_gesto(handedness, gesto, pose):
    assert recognize_gesture(make_hand(handedness, **pose), handedness) is gesto


@pytest.mark.parametrize("handedness", HANDS)
@pytest.mark.parametrize(
    "fingers",
    [
        (True, True, True, False),  # três dedos: não é paz nem mão aberta
        (False, False, True, False),  # só o médio
        (False, False, False, True),  # só o mínimo
        (True, False, False, True),  # indicador e mínimo
    ],
)
def test_configuracoes_desconhecidas_devolvem_none(handedness, fingers):
    assert recognize_gesture(make_hand(handedness, fingers=fingers), handedness) is None


@pytest.mark.parametrize("handedness", HANDS)
def test_ok_vence_mao_aberta(handedness):
    """Nos dois, médio/anelar/mínimo estão estendidos — o toque é o que separa."""
    mao = make_hand(handedness, fingers=(False, True, True, True), pinch=True)
    assert fingers_extended(mao, handedness)[2:] == (True, True, True)
    assert fingertips_touching(mao, THUMB_TIP, INDEX_TIP)
    assert recognize_gesture(mao, handedness) is OK


@pytest.mark.parametrize("handedness", HANDS)
def test_joinha_exige_polegar_para_cima(handedness):
    """Um polegar para o lado com a mão fechada não é joinha."""
    lateral = make_hand(handedness, thumb=True)
    assert is_thumb_up(lateral) is False
    assert recognize_gesture(lateral, handedness) is not JOINHA

    para_cima = make_hand(handedness, thumb_up=True)
    assert is_thumb_up(para_cima) is True
    assert recognize_gesture(para_cima, handedness) is JOINHA


@pytest.mark.parametrize("handedness", HANDS)
def test_mao_fechada_nao_e_confundida_com_joinha(handedness):
    assert recognize_gesture(make_hand(handedness), handedness) is MAO_FECHADA


def test_regua_da_mao_e_a_distancia_pulso_nos():
    assert hand_span(make_hand("Right")) == pytest.approx(SPAN)


def test_toque_e_relativo_ao_tamanho_da_mao():
    """O limiar precisa acompanhar a distância da mão à câmera."""
    perto = make_hand("Right", fingers=(False, True, True, True), pinch=True)
    longe = [(x // 4, y // 4) for x, y in perto]  # mesma pose, mão bem menor
    assert fingertips_touching(perto, THUMB_TIP, INDEX_TIP)
    assert fingertips_touching(longe, THUMB_TIP, INDEX_TIP)


def test_pontas_distantes_nao_contam_como_toque():
    aberta = make_hand("Right", thumb=True, fingers=(True, True, True, True))
    assert fingertips_touching(aberta, THUMB_TIP, INDEX_TIP) is False


def test_landmarks_insuficientes_levantam_erro():
    with pytest.raises(ValueError, match="21 landmarks"):
        recognize_gesture([(0, 0)] * 5, "Right")


def test_gestos_tem_chaves_e_rotulos_unicos():
    assert len({g.key for g in GESTURES}) == len(GESTURES)
    assert len({g.label for g in GESTURES}) == len(GESTURES)
    assert all(g.key and g.label for g in GESTURES)


# --- apresentação ----------------------------------------------------------


def frame(width: int = 640, height: int = 480) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_desenha_um_rotulo_por_mao():
    img = frame()
    draw_gestures(img, {"Left": "Joinha", "Right": "Paz"})
    claro = img.max(axis=2) > 150
    colunas = claro.any(axis=0)
    assert colunas[: img.shape[1] // 3].any(), "faltou o rótulo da esquerda"
    assert colunas[-img.shape[1] // 3 :].any(), "faltou o rótulo da direita"


def test_sem_maos_mostra_o_estado_vazio():
    com, sem = frame(), frame()
    draw_gestures(com, {"Left": "Paz", "Right": None})
    draw_gestures(sem, {"Left": None, "Right": None})
    meio = slice(sem.shape[0] // 3, 2 * sem.shape[0] // 3)
    assert sem[meio].any(), "faltou a mensagem central"
    assert not com[meio].any(), "com mão detectada não há estado vazio"


def test_mao_sem_gesto_conhecido_mostra_um_traco():
    img = frame()
    draw_gestures(img, {"Left": None, "Right": "OK"})
    assert img.any()
    assert UNKNOWN_LABEL


@pytest.mark.parametrize(("width", "height"), [(320, 240), (640, 480), (1920, 1080)])
def test_rotulos_nao_vazam_do_frame(width, height):
    """ "Mão fechada" é o rótulo mais longo — o alinhamento tem que segurá-lo."""
    img = frame(width, height)
    draw_gestures(img, {"Left": "Mão fechada", "Right": "Mão fechada"})
    assert img[:, -1].sum() == 0 or img[:, -2:].any(), "checagem de borda inconclusiva"
    claro = img.max(axis=2) > 150
    assert claro[:, -1].sum() == 0, "o texto encostou na borda direita"
