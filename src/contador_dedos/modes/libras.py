"""Modo "Números em Libras": reconhece os numerais pela configuração da mão.

**Cobertura atual: 1 a 5.** Os numerais 0 e 6 a 10 ficaram de fora de propósito:
6 a 9 usam configurações que não se reduzem a "N dedos estendidos" e **variam por
região**, e o 10, em várias variantes, envolve **movimento** — que um
reconhecedor de frame único não captura. Chutar a configuração de uma língua
real seria pior que não cobrir: quem usa Libras é quem pagaria pelo erro.

O que distingue este modo do "Contar Dedos" é *quais* dedos estão estendidos, e
não quantos: três dedos quaisquer somam 3, mas só polegar+indicador+médio é o
numeral **3** em Libras.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..core.overlay import draw_hand_landmarks
from ..core.pipeline import ValueSmoother
from ..ui.widgets import draw_hand_readout
from ..vision.hands import HandTracker, real_hand
from ..vision.handshape import fingers_extended
from ..vision.landmarks import Point, landmarks_to_pixels
from .base import Mode

#: Configuração da mão: (polegar, indicador, médio, anelar, mínimo).
HandShape = tuple[bool, bool, bool, bool, bool]


@dataclass(frozen=True)
class LibrasNumber:
    """Um numeral e a configuração de mão que o representa."""

    value: int
    word: str
    shape: HandShape

    @property
    def label(self) -> str:
        """O texto mostrado na tela: o algarismo e o nome por extenso."""
        return f"{self.value} · {self.word}"


#: Numerais cobertos, na variante mais difundida de Libras.
LIBRAS_NUMBERS: tuple[LibrasNumber, ...] = (
    LibrasNumber(1, "um", (False, True, False, False, False)),
    LibrasNumber(2, "dois", (False, True, True, False, False)),
    LibrasNumber(3, "três", (True, True, True, False, False)),
    LibrasNumber(4, "quatro", (False, True, True, True, True)),
    LibrasNumber(5, "cinco", (True, True, True, True, True)),
)

#: Numerais ainda **não** cobertos — ver o cabeçalho do módulo.
PENDING_NUMBERS: tuple[int, ...] = (0, 6, 7, 8, 9, 10)

#: Nota permanente na tela, para o usuário não achar que 7 "não funcionou".
COVERAGE_CAPTION = "Reconhece 1 a 5 — 0 e 6 a 10 ainda não"


def recognize_number(landmarks: Sequence[Point], handedness: str) -> LibrasNumber | None:
    """Identifica o numeral, ou ``None`` se a mão não formar nenhum coberto.

    Args:
        landmarks: os 21 landmarks da mão em pixels.
        handedness: ``"Left"`` ou ``"Right"``, como o MediaPipe reportou.
    """
    shape = fingers_extended(landmarks, handedness)
    for number in LIBRAS_NUMBERS:
        if number.shape == shape:
            return number
    return None


class LibrasNumbers(Mode):
    """Mostra o numeral em Libras formado por cada mão."""

    name = "Libras"
    icon = "🔢"
    hint = "ESC volta ao menu  •  Q encerra"

    def __init__(self, tracker: HandTracker, mirrored: bool = True, smooth_window: int = 5) -> None:
        self._tracker = tracker
        self._mirrored = mirrored
        self._smoothers = {
            "Left": ValueSmoother(smooth_window),
            "Right": ValueSmoother(smooth_window),
        }

    @classmethod
    def from_config(cls, config, tracker: HandTracker) -> LibrasNumbers:
        return cls(tracker, mirrored=config.mirror, smooth_window=config.smooth_window)

    def process(self, frame, timestamp_ms: int = 0):
        height, width = frame.shape[:2]
        leituras: dict[str, str | None] = {"Left": None, "Right": None}

        for hand in self._tracker.detect(frame, timestamp_ms):
            draw_hand_landmarks(frame, hand.landmarks)
            points = landmarks_to_pixels(hand.landmarks, width, height)
            numero = recognize_number(points, hand.handedness)
            leituras[real_hand(hand.handedness, self._mirrored)] = numero.label if numero else None

        suavizado = {hand: self._smoothers[hand].update(valor) for hand, valor in leituras.items()}
        draw_hand_readout(
            frame,
            suavizado,
            self._mirrored,
            caption=COVERAGE_CAPTION,
            empty_message="Mostre a mão para a câmera",
        )
        return frame

    def close(self) -> None:
        """O detector é compartilhado — quem o criou é que o libera."""
