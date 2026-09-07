"""Anotação do frame com os dados da camada de visão."""

from __future__ import annotations

from mediapipe.tasks.python.vision import (
    HandLandmarksConnections,
    drawing_styles,
    drawing_utils,
)

_LANDMARK_STYLE = drawing_styles.get_default_hand_landmarks_style()
_CONNECTION_STYLE = drawing_styles.get_default_hand_connections_style()


def draw_hand_landmarks(img, landmarks) -> None:
    """Desenha os pontos e as conexões de uma mão detectada."""
    drawing_utils.draw_landmarks(
        img,
        landmarks,
        HandLandmarksConnections.HAND_CONNECTIONS,
        _LANDMARK_STYLE,
        _CONNECTION_STYLE,
    )
