"""Testes da lógica de contagem — pura, sem câmera e sem modelo."""

from __future__ import annotations

import pytest

from contador_dedos.modes.finger_counter import count_fingers
from contador_dedos.vision.hands import real_hand
from contador_dedos.vision.handshape import fingers_extended, is_thumb_extended
from contador_dedos.vision.landmarks import LANDMARK_COUNT
from helpers import make_hand

HANDS = ("Left", "Right")


@pytest.mark.parametrize("handedness", HANDS)
@pytest.mark.parametrize(
    ("thumb", "fingers", "expected"),
    [
        (False, (False, False, False, False), 0),  # punho fechado
        (True, (False, False, False, False), 1),  # só o polegar
        (False, (True, False, False, False), 1),  # só o indicador
        (False, (True, True, False, False), 2),  # "paz"
        (True, (True, False, False, True), 3),  # gesto do "chifre"/shaka
        (False, (True, True, True, True), 4),  # quatro, polegar recolhido
        (True, (True, True, True, True), 5),  # mão aberta
    ],
)
def test_conta_dedos_levantados(handedness, thumb, fingers, expected):
    assert count_fingers(make_hand(handedness, thumb, fingers), handedness) == expected


@pytest.mark.parametrize("handedness", HANDS)
def test_cada_dedo_longo_conta_uma_vez(handedness):
    """Levantar um dedo de cada vez soma exatamente um."""
    for index in range(4):
        fingers = [False] * 4
        fingers[index] = True
        assert count_fingers(make_hand(handedness, False, fingers), handedness) == 1


@pytest.mark.parametrize("handedness", HANDS)
def test_polegar_depende_da_lateralidade(handedness):
    """O mesmo polegar estendido some se a mão for lida com o rótulo trocado.

    É exatamente o bug que o P0 #7 descrevia: sem a lateralidade correta, o
    polegar é contado para o lado errado.
    """
    outra = "Left" if handedness == "Right" else "Right"
    aberta = make_hand(handedness, thumb=True)
    assert is_thumb_extended(aberta, handedness) is True
    assert is_thumb_extended(aberta, outra) is False
    assert count_fingers(aberta, handedness) == 1
    assert count_fingers(aberta, outra) == 0


def test_landmarks_insuficientes_levanta_erro():
    with pytest.raises(ValueError, match="21 landmarks"):
        count_fingers([(0, 0)] * 5, "Right")


def test_aceita_exatamente_21_landmarks():
    assert len(make_hand("Right")) == LANDMARK_COUNT
    assert count_fingers(make_hand("Right"), "Right") == 0


@pytest.mark.parametrize(
    ("rotulo", "espelhado", "esperado"),
    [
        ("Right", True, "Right"),  # com flip, o rótulo já é a mão real
        ("Left", True, "Left"),
        ("Right", False, "Left"),  # sem flip, o MediaPipe entrega trocado
        ("Left", False, "Right"),
    ],
)
def test_real_hand(rotulo, espelhado, esperado):
    assert real_hand(rotulo, espelhado) == esperado


@pytest.mark.parametrize("espelhado", [True, False])
def test_real_hand_e_involutivo(espelhado):
    """Aplicar a conversão duas vezes com o mesmo espelhamento volta ao início."""
    for rotulo in HANDS:
        assert real_hand(real_hand(rotulo, espelhado), espelhado) == rotulo


@pytest.mark.parametrize("handedness", HANDS)
def test_contagem_e_a_soma_dos_dedos_estendidos(handedness):
    """A contagem e os gestos leem a mesma primitiva — não podem divergir."""
    for thumb in (False, True):
        for fingers in [(False,) * 4, (True, True, False, False), (True,) * 4]:
            mao = make_hand(handedness, thumb, fingers)
            assert count_fingers(mao, handedness) == sum(fingers_extended(mao, handedness))
