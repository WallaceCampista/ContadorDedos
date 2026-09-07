"""Helpers de desenho sobre o frame: texto, landmarks, FPS e barra de status."""

from __future__ import annotations

import cv2
from mediapipe.tasks.python.vision import (
    HandLandmarksConnections,
    drawing_styles,
    drawing_utils,
)

from ..vision.landmarks import Point
from .theme import (
    COLOR_HINT,
    COLOR_OUTLINE,
    COLOR_TEXT,
    FONT,
    HUD_REFERENCE_HEIGHT,
    MIN_HUD_SCALE,
)

_LANDMARK_STYLE = drawing_styles.get_default_hand_landmarks_style()
_CONNECTION_STYLE = drawing_styles.get_default_hand_connections_style()


def hud_scale(height: int) -> float:
    """Fator de escala do HUD, para o texto ficar legível em qualquer resolução.

    Os tamanhos foram desenhados para 480px de altura; em uma webcam 1080p o
    HUD sem escala vira um detalhe ilegível no canto.
    """
    return max(height / HUD_REFERENCE_HEIGHT, MIN_HUD_SCALE)


def draw_text(
    img,
    text: str,
    org: Point,
    scale: float = 0.6,
    color: tuple[int, int, int] = COLOR_TEXT,
    thickness: int = 1,
) -> None:
    """Escreve com contorno preto, para o texto não sumir em fundos claros."""
    cv2.putText(img, text, org, FONT, scale, COLOR_OUTLINE, thickness + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, FONT, scale, color, thickness, cv2.LINE_AA)


def draw_hand_landmarks(img, landmarks) -> None:
    """Desenha os pontos e as conexões de uma mão detectada."""
    drawing_utils.draw_landmarks(
        img,
        landmarks,
        HandLandmarksConnections.HAND_CONNECTIONS,
        _LANDMARK_STYLE,
        _CONNECTION_STYLE,
    )


def draw_status_bar(img, hint: str, fps: float) -> None:
    """Rodapé comum a todas as telas: FPS à esquerda, atalhos à direita."""
    height, width = img.shape[:2]
    scale = hud_scale(height)
    footer_y = height - int(12 * scale)
    footer_scale = 0.5 * scale
    thickness = max(1, int(scale))

    fps_org = (int(10 * scale), footer_y)
    draw_text(img, f"{fps:4.1f} FPS", fps_org, footer_scale, COLOR_HINT, thickness)
    (hint_width, _), _ = cv2.getTextSize(hint, FONT, footer_scale, thickness)
    draw_text(
        img,
        hint,
        (width - hint_width - int(10 * scale), footer_y),
        footer_scale,
        COLOR_HINT,
        thickness,
    )
