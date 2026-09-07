"""Modo "Gestos": reconhece configurações de mão a partir dos landmarks.

O reconhecimento é **geométrico e puro** — não usa o `GestureRecognizer` do
MediaPipe. Duas razões: reaproveita o detector de mãos que já está carregado,
sem um segundo modelo para baixar; e o conjunto pronto do MediaPipe não inclui
o "OK", que a Seção 6 do plano pede.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..core.overlay import draw_hand_landmarks
from ..core.pipeline import ValueSmoother
from ..ui.widgets import UNKNOWN_VALUE, draw_hand_readout
from ..vision.hands import HandTracker, real_hand
from ..vision.handshape import fingers_extended, fingertips_touching, is_thumb_up
from ..vision.landmarks import INDEX_TIP, THUMB_TIP, Point, landmarks_to_pixels
from .base import Mode


@dataclass(frozen=True)
class Gesture:
    """Um gesto reconhecível."""

    key: str
    label: str


JOINHA = Gesture("joinha", "Joinha")
PAZ = Gesture("paz", "Paz")
OK = Gesture("ok", "OK")
MAO_ABERTA = Gesture("aberta", "Mão aberta")
MAO_FECHADA = Gesture("fechada", "Mão fechada")

#: Todos os gestos conhecidos, na ordem em que são testados.
GESTURES: tuple[Gesture, ...] = (OK, JOINHA, PAZ, MAO_ABERTA, MAO_FECHADA)


def recognize_gesture(landmarks: Sequence[Point], handedness: str) -> Gesture | None:
    """Identifica o gesto de uma mão, ou ``None`` se não for nenhum conhecido.

    A ordem dos testes importa: o "OK" precisa vir antes de "mão aberta",
    porque nos dois casos médio, anelar e mínimo estão estendidos — o que os
    separa é o indicador encostando no polegar.

    Args:
        landmarks: os 21 landmarks da mão em pixels.
        handedness: ``"Left"`` ou ``"Right"``, como o MediaPipe reportou.
    """
    thumb, index, middle, ring, pinky = fingers_extended(landmarks, handedness)
    longos = (index, middle, ring, pinky)

    if all((middle, ring, pinky)) and fingertips_touching(landmarks, THUMB_TIP, INDEX_TIP):
        return OK
    if is_thumb_up(landmarks) and not any(longos):
        return JOINHA
    if index and middle and not ring and not pinky:
        return PAZ
    if thumb and all(longos):
        return MAO_ABERTA
    if not thumb and not any(longos):
        return MAO_FECHADA
    return None


# ---------------------------------------------------------------------------
# Apresentação
# ---------------------------------------------------------------------------

#: Texto mostrado quando a mão não forma nenhum gesto conhecido.
UNKNOWN_LABEL = UNKNOWN_VALUE


def draw_gestures(img, leituras: dict[str, str | None], mirrored: bool = True) -> None:
    """Desenha o gesto reconhecido em cada mão."""
    draw_hand_readout(img, leituras, mirrored, empty_message="Mostre a mão para a câmera")


class GestureRecognizer(Mode):
    """Reconhece joinha, paz, OK e mão aberta/fechada em tempo real."""

    name = "Gestos"
    icon = "🤟"
    hint = "ESC volta ao menu  •  Q encerra"

    def __init__(self, tracker: HandTracker, mirrored: bool = True, smooth_window: int = 5) -> None:
        self._tracker = tracker
        self._mirrored = mirrored
        self._smoothers = {
            "Left": ValueSmoother(smooth_window),
            "Right": ValueSmoother(smooth_window),
        }

    @classmethod
    def from_config(cls, config, tracker: HandTracker) -> GestureRecognizer:
        return cls(tracker, mirrored=config.mirror, smooth_window=config.smooth_window)

    def process(self, frame, timestamp_ms: int = 0):
        height, width = frame.shape[:2]
        leituras: dict[str, str | None] = {"Left": None, "Right": None}

        for hand in self._tracker.detect(frame, timestamp_ms):
            draw_hand_landmarks(frame, hand.landmarks)
            points = landmarks_to_pixels(hand.landmarks, width, height)
            gesto = recognize_gesture(points, hand.handedness)
            leituras[real_hand(hand.handedness, self._mirrored)] = gesto.label if gesto else None

        suavizado = {hand: self._smoothers[hand].update(valor) for hand, valor in leituras.items()}
        draw_gestures(frame, suavizado, self._mirrored)
        return frame

    def close(self) -> None:
        """O detector é compartilhado — quem o criou é que o libera."""
