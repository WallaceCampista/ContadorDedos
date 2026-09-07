"""Registro dos modos disponíveis.

Adicionar uma feature ao app é escrever a subclasse de
:class:`~contador_dedos.modes.base.Mode` e acrescentar a sua fábrica aqui — o
loop principal e (a partir da Fase 4) o menu se atualizam sozinhos.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import Callable

from .base import Mode
from .finger_counter import FingerCounter

#: Uma fábrica recebe a configuração e devolve um modo pronto para usar.
ModeFactory = Callable[..., Mode]

#: O registro. A ordem aqui é a ordem dos cards no menu.
MODE_FACTORIES: tuple[ModeFactory, ...] = (FingerCounter.from_config,)


def build_modes(config) -> list[Mode]:
    """Instancia todos os modos registrados."""
    return [factory(config) for factory in MODE_FACTORIES]


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


__all__ = ["MODE_FACTORIES", "FingerCounter", "Mode", "ModeFactory", "build_modes", "close_modes"]
