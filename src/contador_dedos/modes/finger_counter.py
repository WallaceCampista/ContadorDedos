"""Modo "Contar Dedos": a lógica de contagem e a sua apresentação.

A regra de negócio (:func:`count_fingers`) é pura — recebe landmarks em pixels e
devolve um número. É isso que permite testá-la sem webcam e sem modelo.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..core.overlay import draw_hand_landmarks
from ..core.pipeline import ValueSmoother
from ..ui.theme import COLOR_TEXT, COLOR_TOTAL
from ..ui.widgets import Rect, draw_center_message, draw_panel, draw_text, hud_scale
from ..vision.hands import HandTracker, real_hand
from ..vision.handshape import fingers_extended
from ..vision.landmarks import Point, landmarks_to_pixels
from .base import Mode

# ---------------------------------------------------------------------------
# Lógica pura
# ---------------------------------------------------------------------------


def count_fingers(landmarks: Sequence[Point], handedness: str) -> int:
    """Conta quantos dedos estão levantados em uma mão.

    Args:
        landmarks: os 21 landmarks da mão em pixels, na ordem do MediaPipe.
        handedness: ``"Left"`` ou ``"Right"``, como reportado pelo MediaPipe
            para o frame processado.

    Como o rótulo do MediaPipe e a geometria da imagem seguem a mesma convenção
    de espelhamento, o resultado independe de o frame ter sido espelhado ou não;
    o que muda é apenas a qual mão real aquele rótulo corresponde.
    """
    return sum(fingers_extended(landmarks, handedness))


# ---------------------------------------------------------------------------
# Apresentação
# ---------------------------------------------------------------------------


def draw_counter(
    img,
    label: str,
    value: int | None,
    x: int,
    scale: float,
    color: tuple[int, int, int] = COLOR_TEXT,
) -> None:
    """Desenha um rótulo e, logo abaixo, o valor daquele contador."""
    draw_text(img, label, (x, int(30 * scale)), 0.5 * scale, thickness=max(1, int(scale)))
    draw_text(
        img,
        "-" if value is None else str(value),
        (x + int(20 * scale), int(80 * scale)),
        2.0 * scale,
        color,
        max(2, int(5 * scale)),
    )


def draw_counters(img, counts: dict[str, int | None], mirrored: bool) -> None:
    """Desenha os contadores de cada mão e o total, sobre uma faixa legível."""
    height, width = img.shape[:2]
    scale = hud_scale(height)
    draw_panel(img, Rect(0, 0, width, int(96 * scale)))

    # Cada painel fica do lado da tela em que aquela mão realmente aparece.
    left_hand, right_hand = ("Left", "Right") if mirrored else ("Right", "Left")
    draw_counter(
        img, "Esquerda" if mirrored else "Direita", counts[left_hand], int(10 * scale), scale
    )
    draw_counter(
        img,
        "Direita" if mirrored else "Esquerda",
        counts[right_hand],
        width - int(130 * scale),
        scale,
    )

    total = sum(value for value in counts.values() if value is not None)
    draw_counter(img, "Total", total, width // 2 - int(30 * scale), scale, COLOR_TOTAL)

    if all(value is None for value in counts.values()):
        draw_center_message(img, "Nenhuma mão detectada", scale)


# ---------------------------------------------------------------------------
# O modo
# ---------------------------------------------------------------------------


class FingerCounter(Mode):
    """Conta os dedos levantados de cada mão e mostra o total."""

    name = "Contar Dedos"
    icon = "✋"
    hint = "ESC volta ao menu  •  Q encerra"

    def __init__(self, tracker: HandTracker, mirrored: bool = True, smooth_window: int = 5) -> None:
        self._tracker = tracker
        self._mirrored = mirrored
        self._smoothers = {
            "Left": ValueSmoother(smooth_window),
            "Right": ValueSmoother(smooth_window),
        }

    @classmethod
    def from_config(cls, config, tracker: HandTracker) -> FingerCounter:
        return cls(tracker, mirrored=config.mirror, smooth_window=config.smooth_window)

    def process(self, frame, timestamp_ms: int = 0):
        height, width = frame.shape[:2]
        counts: dict[str, int | None] = {"Left": None, "Right": None}

        for hand in self._tracker.detect(frame, timestamp_ms):
            draw_hand_landmarks(frame, hand.landmarks)
            points = landmarks_to_pixels(hand.landmarks, width, height)
            counts[real_hand(hand.handedness, self._mirrored)] = count_fingers(
                points, hand.handedness
            )

        smoothed = {hand: self._smoothers[hand].update(value) for hand, value in counts.items()}
        draw_counters(frame, smoothed, self._mirrored)
        return frame

    def close(self) -> None:
        """O detector é compartilhado — quem o criou é que o libera."""
