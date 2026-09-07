"""Modo "Contar Dedos": a lógica de contagem e a sua apresentação.

A regra de negócio (:func:`count_fingers`) é pura — recebe landmarks em pixels e
devolve um número. É isso que permite testá-la sem webcam e sem modelo.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Sequence

from ..core.overlay import draw_hand_landmarks, draw_text, hud_scale
from ..core.theme import COLOR_TEXT, COLOR_TOTAL
from ..vision.hands import HandTracker, real_hand
from ..vision.landmarks import (
    FINGER_TIP_IDS,
    PIP_OFFSET,
    THUMB_IP,
    THUMB_TIP,
    Point,
    landmarks_to_pixels,
    validate,
)
from .base import Mode

# ---------------------------------------------------------------------------
# Lógica pura
# ---------------------------------------------------------------------------


def is_thumb_extended(landmarks: Sequence[Point], handedness: str) -> bool:
    """Diz se o polegar está estendido.

    ``handedness`` é o rótulo devolvido pelo MediaPipe (``"Left"``/``"Right"``)
    **para o mesmo frame** de onde vieram os landmarks. O MediaPipe classifica
    a lateralidade assumindo uma imagem espelhada, e essa mesma convenção fixa
    o sentido em que o polegar aponta no eixo X — por isso a regra abaixo vale
    tanto com quanto sem ``cv2.flip`` (ver :func:`count_fingers`).
    """
    if handedness == "Right":
        return landmarks[THUMB_TIP][0] > landmarks[THUMB_IP][0]
    return landmarks[THUMB_TIP][0] < landmarks[THUMB_IP][0]


def count_fingers(landmarks: Sequence[Point], handedness: str) -> int:
    """Conta quantos dedos estão levantados em uma mão.

    Args:
        landmarks: os 21 landmarks da mão em pixels, na ordem do MediaPipe.
        handedness: ``"Left"`` ou ``"Right"``, como reportado pelo MediaPipe
            para o frame processado.

    Os quatro dedos longos contam como levantados quando a ponta está *acima*
    da articulação PIP (Y menor, pois o eixo cresce para baixo). O polegar usa
    o eixo X, porque ele se abre lateralmente — daí depender da lateralidade.

    Como o rótulo do MediaPipe e a geometria da imagem seguem a mesma convenção
    de espelhamento, o resultado independe de o frame ter sido espelhado ou não;
    o que muda é apenas a qual mão real aquele rótulo corresponde.
    """
    validate(landmarks)

    count = 1 if is_thumb_extended(landmarks, handedness) else 0
    for tip in FINGER_TIP_IDS:
        if landmarks[tip][1] < landmarks[tip - PIP_OFFSET][1]:
            count += 1
    return count


class CountSmoother:
    """Anti-flicker: devolve o valor mais frequente das últimas N leituras.

    ``None`` representa "mão ausente" e também entra na janela, de modo que o
    contador some suavemente quando a mão sai do quadro.
    """

    def __init__(self, window: int = 5) -> None:
        if window < 1:
            raise ValueError("A janela de suavização precisa ser >= 1.")
        self._history: deque[int | None] = deque(maxlen=window)

    def update(self, value: int | None) -> int | None:
        self._history.append(value)
        return Counter(self._history).most_common(1)[0][0]


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
    """Desenha os contadores de cada mão e o total."""
    height, width = img.shape[:2]
    scale = hud_scale(height)

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


# ---------------------------------------------------------------------------
# O modo
# ---------------------------------------------------------------------------


class FingerCounter(Mode):
    """Conta os dedos levantados de cada mão e mostra o total."""

    name = "Contar Dedos"
    icon = "✋"
    hint = "Q ou ESC para sair"

    def __init__(self, tracker: HandTracker, mirrored: bool = True, smooth_window: int = 5) -> None:
        self._tracker = tracker
        self._mirrored = mirrored
        self._smoothers = {
            "Left": CountSmoother(smooth_window),
            "Right": CountSmoother(smooth_window),
        }

    @classmethod
    def from_config(cls, config) -> FingerCounter:
        """Constrói o modo (e o seu detector) a partir da configuração."""
        tracker = HandTracker(
            model_path=config.model_path,
            max_hands=config.max_hands,
            detection_confidence=config.detection_confidence,
            tracking_confidence=config.tracking_confidence,
        )
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
        self._tracker.close()
