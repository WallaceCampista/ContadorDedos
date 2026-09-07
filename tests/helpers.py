"""Mãos sintéticas — permitem testar contagem e gestos sem webcam e sem modelo.

A mão é montada com geometria coerente (pulso, nós, falanges), e não com pontos
soltos: os gestos dependem de distâncias reais entre landmarks, não só da
relação ponta/articulação que a contagem usa.
"""

from __future__ import annotations

from collections.abc import Sequence

from contador_dedos.vision.landmarks import (
    FINGER_TIP_IDS,
    LANDMARK_COUNT,
    THUMB_IP,
    THUMB_MCP,
    THUMB_TIP,
)

#: Régua da mão sintética: distância do pulso à base do médio.
SPAN = 100
_WRIST_XY = (200, 400)
#: Y da fileira de nós (MCP). O eixo cresce para baixo.
_MCP_Y = _WRIST_XY[1] - SPAN
#: Deslocamento em X de cada dedo longo, do lado do polegar para o mínimo.
_FINGER_OFFSETS = (25, 0, -25, -50)


def make_hand(
    handedness: str,
    thumb: bool = False,
    fingers: Sequence[bool] = (False, False, False, False),
    thumb_up: bool = False,
    pinch: bool = False,
) -> list[tuple[int, int]]:
    """Monta os 21 landmarks de uma mão, palma para a câmera e dedos para cima.

    Args:
        handedness: ``"Left"`` ou ``"Right"``, na convenção do MediaPipe. Define
            para que lado do eixo X o polegar se abre.
        thumb: polegar estendido lateralmente.
        fingers: indicador, médio, anelar e mínimo, nessa ordem.
        thumb_up: polegar apontando para cima (o joinha), em vez de para o lado.
        pinch: ponta do indicador encostada na do polegar (o "OK"). Sobrepõe o
            que ``fingers`` disser sobre o indicador.
    """
    if len(fingers) != len(FINGER_TIP_IDS):
        raise ValueError(f"Esperava {len(FINGER_TIP_IDS)} dedos, recebi {len(fingers)}.")

    side = 1 if handedness == "Right" else -1
    wrist_x, wrist_y = _WRIST_XY
    points = [(0, 0)] * LANDMARK_COUNT
    points[0] = _WRIST_XY

    # Polegar: CMC, MCP, IP e ponta, abrindo para o lado do dedo indicador.
    points[1] = (wrist_x + side * 20, wrist_y - 20)
    points[THUMB_MCP] = (wrist_x + side * 40, wrist_y - 50)
    if thumb_up:
        points[THUMB_IP] = (wrist_x + side * 45, wrist_y - 100)
        points[THUMB_TIP] = (wrist_x + side * 50, wrist_y - 150)
    else:
        points[THUMB_IP] = (wrist_x + side * 60, wrist_y - 75)
        # Estendido: a ponta passa da articulação no eixo X. Recolhido: fica aquém.
        points[THUMB_TIP] = (wrist_x + side * (80 if thumb else 40), wrist_y - 90)

    # Dedos longos: MCP, PIP, DIP e ponta, empilhados acima do nó.
    for tip, offset, raised in zip(FINGER_TIP_IDS, _FINGER_OFFSETS, fingers):
        x = wrist_x + side * offset
        points[tip - 3] = (x, _MCP_Y)
        points[tip - 2] = (x, _MCP_Y - 30)
        points[tip - 1] = (x, _MCP_Y - 50)
        # Levantado: ponta acima do PIP. Recolhido: dobrada para dentro da palma.
        points[tip] = (x, _MCP_Y - 70 if raised else _MCP_Y + 10)

    if pinch:
        # Indicador e polegar se encontram — as duas pontas no mesmo ponto.
        encontro = (wrist_x + side * 55, wrist_y - 110)
        points[THUMB_TIP] = encontro
        points[FINGER_TIP_IDS[0]] = encontro

    return points
