"""Testes dos numerais em Libras — configuração de mão, sem câmera."""

from __future__ import annotations

import numpy as np
import pytest

from contador_dedos.modes.finger_counter import count_fingers
from contador_dedos.modes.libras import (
    COVERAGE_CAPTION,
    LIBRAS_NUMBERS,
    PENDING_NUMBERS,
    LibrasNumbers,
    recognize_number,
)
from contador_dedos.ui.widgets import UNKNOWN_VALUE, draw_hand_readout
from helpers import make_hand

HANDS = ("Left", "Right")

#: Como montar cada numeral na mão sintética: (polegar, dedos longos).
POSES = {
    1: (False, (True, False, False, False)),
    2: (False, (True, True, False, False)),
    3: (True, (True, True, False, False)),
    4: (False, (True, True, True, True)),
    5: (True, (True, True, True, True)),
}


@pytest.mark.parametrize("handedness", HANDS)
@pytest.mark.parametrize("valor", sorted(POSES))
def test_reconhece_os_numerais_cobertos(handedness, valor):
    thumb, fingers = POSES[valor]
    numero = recognize_number(make_hand(handedness, thumb, fingers), handedness)
    assert numero is not None
    assert numero.value == valor


@pytest.mark.parametrize("handedness", HANDS)
def test_tres_dedos_quaisquer_nao_sao_o_numeral_tres(handedness):
    """É o que separa este modo do contador: importa *quais* dedos, não quantos."""
    outra = make_hand(handedness, False, (True, True, True, False))
    assert count_fingers(outra, handedness) == 3
    assert recognize_number(outra, handedness) is None


@pytest.mark.parametrize("handedness", HANDS)
@pytest.mark.parametrize(
    "fingers",
    [
        (False, False, False, False),  # punho: o zero não é coberto
        (False, True, False, False),  # só o médio
        (False, False, False, True),  # só o mínimo
        (True, False, False, True),  # indicador e mínimo
    ],
)
def test_configuracoes_nao_cobertas_devolvem_none(handedness, fingers):
    assert recognize_number(make_hand(handedness, False, fingers), handedness) is None


@pytest.mark.parametrize("handedness", HANDS)
def test_polegar_distingue_o_tres_do_dois(handedness):
    dois = make_hand(handedness, False, (True, True, False, False))
    tres = make_hand(handedness, True, (True, True, False, False))
    assert recognize_number(dois, handedness).value == 2
    assert recognize_number(tres, handedness).value == 3


@pytest.mark.parametrize("handedness", HANDS)
def test_polegar_distingue_o_quatro_do_cinco(handedness):
    quatro = make_hand(handedness, False, (True, True, True, True))
    cinco = make_hand(handedness, True, (True, True, True, True))
    assert recognize_number(quatro, handedness).value == 4
    assert recognize_number(cinco, handedness).value == 5


def test_cada_configuracao_mapeia_um_numeral_so():
    """Duas entradas com a mesma forma tornariam o reconhecimento ambíguo."""
    formas = [numero.shape for numero in LIBRAS_NUMBERS]
    assert len(set(formas)) == len(formas)


def test_cobertura_declarada_bate_com_a_implementada():
    cobertos = {numero.value for numero in LIBRAS_NUMBERS}
    assert cobertos == {1, 2, 3, 4, 5}
    assert cobertos.isdisjoint(PENDING_NUMBERS)
    assert cobertos | set(PENDING_NUMBERS) == set(
        range(11)
    ), "0 a 10 precisam estar todos classificados"


def test_rotulo_traz_algarismo_e_palavra():
    numero = next(n for n in LIBRAS_NUMBERS if n.value == 3)
    assert numero.label.startswith("3")
    assert "três" in numero.label


def test_landmarks_insuficientes_levantam_erro():
    with pytest.raises(ValueError, match="21 landmarks"):
        recognize_number([(0, 0)] * 5, "Right")


def test_modo_declara_a_limitacao_na_tela():
    """O usuário precisa saber que o 7 não falhou — ele não é coberto."""
    assert "1 a 5" in COVERAGE_CAPTION
    assert LibrasNumbers.name


# --- apresentação ----------------------------------------------------------


def frame(width: int = 640, height: int = 480) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_a_nota_de_cobertura_e_desenhada():
    com, sem = frame(), frame()
    draw_hand_readout(com, {"Left": "3 · três", "Right": None}, caption=COVERAGE_CAPTION)
    draw_hand_readout(sem, {"Left": "3 · três", "Right": None})
    assert (com != sem).any(), "a nota de cobertura não apareceu"


@pytest.mark.parametrize("mirrored", [True, False])
def test_cada_coluna_fica_do_lado_da_sua_mao(mirrored):
    img = frame()
    draw_hand_readout(img, {"Left": "1 · um", "Right": None}, mirrored)
    claro = img.max(axis=2) > 150
    colunas = claro.any(axis=0)
    esquerda, direita = colunas[: img.shape[1] // 3].any(), colunas[-img.shape[1] // 3 :].any()
    assert esquerda and direita, "as duas colunas são sempre desenhadas"


def test_valor_ausente_mostra_um_traco():
    img = frame()
    draw_hand_readout(img, {"Left": None, "Right": None})
    assert img.any()
    assert UNKNOWN_VALUE == "—"
