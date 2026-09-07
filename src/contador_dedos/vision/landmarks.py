"""Índices dos landmarks da mão — nomes no lugar dos números mágicos.

A ordem é a do MediaPipe: 0 é o pulso e cada dedo ocupa quatro pontos
consecutivos, da base para a ponta.
"""

from __future__ import annotations

from collections.abc import Sequence

#: Quantidade de landmarks que o MediaPipe devolve por mão.
LANDMARK_COUNT = 21

#: Pontas do indicador, médio, anelar e mínimo.
FINGER_TIP_IDS: tuple[int, ...] = (8, 12, 16, 20)
#: A articulação PIP de cada dedo fica dois índices antes da ponta.
PIP_OFFSET = 2
#: Ponta e articulação interfalângica do polegar.
THUMB_TIP, THUMB_IP = 4, 3
#: Base do polegar.
THUMB_MCP = 2
#: Ponta do indicador (o primeiro dos dedos longos).
INDEX_TIP = 8
#: Bases do indicador e do médio, e o pulso — a régua da mão.
INDEX_MCP, MIDDLE_MCP, WRIST = 5, 9, 0

#: Nomes dos dedos, na ordem em que ``fingers_extended`` os devolve.
FINGER_NAMES = ("polegar", "indicador", "médio", "anelar", "mínimo")

#: Um landmark já convertido para pixels da imagem.
Point = tuple[int, int]


def landmarks_to_pixels(landmarks, width: int, height: int) -> list[Point]:
    """Converte landmarks normalizados do MediaPipe para pixels da imagem."""
    return [(int(landmark.x * width), int(landmark.y * height)) for landmark in landmarks]


def validate(landmarks: Sequence[Point]) -> None:
    """Garante que há landmarks suficientes para as regras de contagem."""
    if len(landmarks) <= max(FINGER_TIP_IDS):
        raise ValueError(f"Esperava {LANDMARK_COUNT} landmarks, recebi {len(landmarks)}.")
