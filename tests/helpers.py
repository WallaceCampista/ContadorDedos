"""Mãos sintéticas — permitem testar a contagem sem webcam e sem modelo."""

from __future__ import annotations

from collections.abc import Sequence

from contador_dedos.vision.landmarks import (
    FINGER_TIP_IDS,
    LANDMARK_COUNT,
    PIP_OFFSET,
    THUMB_IP,
    THUMB_TIP,
)


def make_hand(
    handedness: str,
    thumb: bool = False,
    fingers: Sequence[bool] = (False, False, False, False),
) -> list[tuple[int, int]]:
    """Monta os 21 landmarks de uma mão com os dedos pedidos levantados.

    O modelo geométrico é o mesmo que ``count_fingers`` lê: palma para a câmera
    e dedos apontando para cima. Os pontos irrelevantes para a contagem ficam em
    uma posição neutra — o que importa é a relação entre ponta e articulação.

    Args:
        handedness: ``"Left"`` ou ``"Right"``, na convenção do MediaPipe.
        thumb: se o polegar deve estar estendido.
        fingers: indicador, médio, anelar e mínimo, nessa ordem.
    """
    if len(fingers) != len(FINGER_TIP_IDS):
        raise ValueError(f"Esperava {len(FINGER_TIP_IDS)} dedos, recebi {len(fingers)}.")

    points = [(100, 300)] * LANDMARK_COUNT

    # O polegar se abre no eixo X, e o sentido depende da lateralidade.
    points[THUMB_IP] = (120, 250)
    direction = 1 if handedness == "Right" else -1
    points[THUMB_TIP] = (120 + direction * (20 if thumb else -20), 240)

    # Os dedos longos: ponta acima da articulação PIP (Y menor) = levantado.
    for tip, raised in zip(FINGER_TIP_IDS, fingers):
        points[tip - PIP_OFFSET] = (0, 200)
        points[tip] = (0, 150 if raised else 250)

    return points
