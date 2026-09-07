"""Leitura geométrica da mão: quais dedos estão estendidos, tamanho e toques.

Camada puramente matemática sobre os landmarks — sem OpenCV, sem câmera, sem
MediaPipe. É a base compartilhada pela contagem de dedos e pelo reconhecimento
de gestos, e o que permite testar as duas com mãos sintéticas.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from .landmarks import (
    FINGER_TIP_IDS,
    INDEX_MCP,
    MIDDLE_MCP,
    PINKY_MCP,
    PIP_OFFSET,
    THUMB_MCP,
    THUMB_TIP,
    WRIST,
    Point,
    validate,
)

#: Fração da régua da mão abaixo da qual duas pontas contam como encostadas.
TOUCH_RATIO = 0.35
#: Quanto o polegar precisa subir acima dos nós para contar como "para cima".
THUMB_UP_RATIO = 0.15


def distance(a: Point, b: Point) -> float:
    return math.dist(a, b)


def hand_span(landmarks: Sequence[Point]) -> float:
    """A régua da mão: distância do pulso à base do dedo médio.

    Serve para normalizar limiares — sem isso, "as pontas estão encostadas"
    dependeria de a mão estar perto ou longe da câmera.
    """
    validate(landmarks)
    return distance(landmarks[WRIST], landmarks[MIDDLE_MCP])


def is_thumb_extended(landmarks: Sequence[Point], handedness: str | None = None) -> bool:
    """Diz se o polegar está estendido.

    Compara a **ponta** do polegar com a **base dele** (a articulação MCP),
    medindo a distância de cada uma até a base do dedo mínimo — o ponto da palma
    mais afastado do polegar.

    Por que não comparar a ponta com a articulação IP no eixo X, como antes: IP e
    ponta são vizinhas, só a falange distal as separa. Com o polegar aberto de
    lado a diferença é visível, mas com o polegar subindo junto dos dedos ela
    encolhe a poucos pixels e a decisão sai no ruído — era isso que fazia a mão
    aberta contar 4. Da base à ponta o segmento é umas três vezes maior.

    Medir por distância também elimina a dependência da lateralidade: recolher o
    polegar leva a ponta *na direção* do mínimo, encurtando a distância, e isso
    vale para as duas mãos, em qualquer inclinação. ``handedness`` é aceito só
    por compatibilidade com quem já chamava a função, e é ignorado.
    """
    reference = landmarks[PINKY_MCP]
    return distance(landmarks[THUMB_TIP], reference) > distance(landmarks[THUMB_MCP], reference)


def is_thumb_up(landmarks: Sequence[Point]) -> bool:
    """Diz se o polegar aponta para cima, acima dos nós dos dedos.

    O teste do eixo X de :func:`is_thumb_extended` não distingue um polegar
    para cima de um polegar para o lado — e é essa diferença que separa o
    joinha de uma mão fechada qualquer.
    """
    span = hand_span(landmarks)
    return landmarks[THUMB_TIP][1] < landmarks[INDEX_MCP][1] - THUMB_UP_RATIO * span


def fingers_extended(landmarks: Sequence[Point], handedness: str) -> tuple[bool, ...]:
    """Estado dos cinco dedos, na ordem polegar → mínimo.

    Um dedo longo conta como estendido quando a ponta está *acima* da
    articulação PIP (Y menor, pois o eixo cresce para baixo). O polegar usa o
    eixo X, porque ele se abre lateralmente.
    """
    validate(landmarks)
    return (
        is_thumb_extended(landmarks),
        *(landmarks[tip][1] < landmarks[tip - PIP_OFFSET][1] for tip in FINGER_TIP_IDS),
    )


def fingertips_touching(
    landmarks: Sequence[Point],
    first: int,
    second: int,
    ratio: float = TOUCH_RATIO,
) -> bool:
    """Diz se duas pontas estão encostadas, em proporção ao tamanho da mão."""
    span = hand_span(landmarks)
    if span <= 0:
        return False
    return distance(landmarks[first], landmarks[second]) < ratio * span
