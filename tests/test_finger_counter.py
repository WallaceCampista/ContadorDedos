"""Testes da lógica de contagem — pura, sem câmera e sem modelo."""

from __future__ import annotations

import pytest

from contador_dedos.modes.finger_counter import count_fingers
from contador_dedos.vision.hands import real_hand
from contador_dedos.vision.handshape import fingers_extended, is_thumb_extended
from contador_dedos.vision.landmarks import LANDMARK_COUNT, THUMB_IP, THUMB_TIP
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
def test_polegar_nao_depende_mais_da_lateralidade(handedness):
    """A regra por distância vale igual para as duas mãos.

    A versão anterior escolhia o sinal da comparação pelo rótulo do MediaPipe, e
    foi essa dependência que produziu a inversão das mãos.
    """
    aberta = make_hand(handedness, thumb=True)
    assert is_thumb_extended(aberta) is True
    assert is_thumb_extended(aberta, "Right") is is_thumb_extended(aberta, "Left")

    fechada = make_hand(handedness)
    assert is_thumb_extended(fechada) is False


@pytest.mark.parametrize("handedness", HANDS)
def test_polegar_vertical_ainda_conta(handedness):
    """O caso que fazia a mão aberta contar 4.

    Com o polegar subindo junto dos dedos, em vez de aberto de lado, a ponta e a
    articulação IP ficam na mesma coluna: a comparação antiga, entre articulações
    vizinhas no eixo X, não tinha sinal nenhum para decidir.
    """
    mao = make_hand(handedness, thumb_up=True, fingers=(True, True, True, True))
    mao[THUMB_TIP] = (mao[THUMB_IP][0], mao[THUMB_TIP][1])  # polegar na vertical
    assert mao[THUMB_TIP][0] - mao[THUMB_IP][0] == 0, "sem informação no eixo X"
    assert is_thumb_extended(mao) is True
    assert count_fingers(mao, handedness) == 5


@pytest.mark.parametrize("handedness", HANDS)
def test_duas_maos_abertas_somam_dez(handedness):
    """O sintoma relatado: 8 em vez de 10, com as duas mãos abertas."""
    outra = "Left" if handedness == "Right" else "Right"
    esquerda = make_hand(handedness, thumb=True, fingers=(True, True, True, True))
    direita = make_hand(outra, thumb=True, fingers=(True, True, True, True))
    assert count_fingers(esquerda, handedness) + count_fingers(direita, outra) == 10


def test_landmarks_insuficientes_levanta_erro():
    with pytest.raises(ValueError, match="21 landmarks"):
        count_fingers([(0, 0)] * 5, "Right")


def test_aceita_exatamente_21_landmarks():
    assert len(make_hand("Right")) == LANDMARK_COUNT
    assert count_fingers(make_hand("Right"), "Right") == 0


@pytest.mark.parametrize(
    ("rotulo", "espelhado", "esperado"),
    [
        # Com flip, a aparência é o espelho da realidade: a mão direita da
        # pessoa aparece como esquerda, e o MediaPipe rotula pela aparência.
        ("Right", True, "Left"),
        ("Left", True, "Right"),
        # Sem flip, aparência e realidade coincidem.
        ("Right", False, "Right"),
        ("Left", False, "Left"),
    ],
)
def test_real_hand(rotulo, espelhado, esperado):
    assert real_hand(rotulo, espelhado) == esperado


def test_convencao_do_rotulo_e_a_aparencia_na_imagem():
    """Ancora a convenção que custou um bug: o rótulo é aparência, não realidade.

    Estabelecido por duas evidências independentes: o usuário levantando a mão
    direita com o espelho ligado viu a contagem cair no painel "Esquerda"; e o
    código original do projeto, que rodava **sem** espelho, contava o polegar da
    mão direita com ``ponta.x < articulação.x``.

    Uma mão com aparência de direita tem o polegar à esquerda dela. Se algum dia
    o MediaPipe mudar essa convenção, é este teste que quebra primeiro.
    """
    # Mão montada para APARECER como direita: o polegar fica do lado esquerdo
    # dela (X menor). É essa geometria que define a aparência.
    aparenta_direita = make_hand("Right", thumb=True)
    assert aparenta_direita[THUMB_TIP][0] < aparenta_direita[THUMB_IP][0]

    aparenta_esquerda = make_hand("Left", thumb=True)
    assert aparenta_esquerda[THUMB_TIP][0] > aparenta_esquerda[THUMB_IP][0]

    # Com o espelho ligado, quem aparece como esquerda é a direita da pessoa.
    assert real_hand("Left", mirrored=True) == "Right"
    assert real_hand("Right", mirrored=True) == "Left"


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
