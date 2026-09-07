"""Registro dos modos disponíveis.

Adicionar uma feature ao app é escrever a subclasse de
:class:`~contador_dedos.modes.base.Mode` e acrescentar a sua fábrica aqui — o
loop principal e (a partir da Fase 4) o menu se atualizam sozinhos.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import Callable

from ..vision.hands import HandTracker
from .base import Mode
from .face_id import FaceId
from .finger_counter import FingerCounter
from .gesture import GestureRecognizer
from .libras import LibrasNumbers

#: Uma fábrica recebe a configuração e o detector compartilhado.
ModeFactory = Callable[..., Mode]

#: O registro. A ordem aqui é a ordem dos cards no menu.
MODE_FACTORIES: tuple[ModeFactory, ...] = (
    FingerCounter.from_config,
    GestureRecognizer.from_config,
    LibrasNumbers.from_config,
    FaceId.from_config,
)


def build_hand_tracker(config) -> HandTracker:
    """Cria o detector de mãos que os modos compartilham.

    Um detector por modo significaria carregar o mesmo modelo várias vezes; o
    dono é quem o cria, e é quem o fecha.
    """
    return HandTracker(
        model_path=config.model_path,
        max_hands=config.max_hands,
        detection_confidence=config.detection_confidence,
        tracking_confidence=config.tracking_confidence,
    )


def build_modes(config, tracker: HandTracker) -> list[Mode]:
    """Instancia todos os modos registrados, sobre o detector compartilhado."""
    return [factory(config, tracker) for factory in MODE_FACTORIES]


def close_modes(modes: Sequence[Mode]) -> None:
    """Libera os recursos de todos os modos.

    Uma falha ao fechar um modo não impede os demais de fecharem: o objetivo do
    cleanup é justamente não deixar câmera ou modelo presos.
    """
    for mode in modes:
        try:
            mode.close()
        except Exception as error:  # o cleanup não pode abortar por uma falha isolada
            print(f"Aviso: falha ao encerrar o modo {mode.name!r}: {error}", file=sys.stderr)


__all__ = [
    "MODE_FACTORIES",
    "FaceId",
    "FingerCounter",
    "GestureRecognizer",
    "LibrasNumbers",
    "Mode",
    "ModeFactory",
    "build_hand_tracker",
    "build_modes",
    "close_modes",
]
