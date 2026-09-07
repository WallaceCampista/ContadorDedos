"""A tela inicial: cards clicáveis sobre a imagem da webcam.

O menu é *data-driven*: recebe as entradas prontas e monta o layout. Registrar
um modo novo em :mod:`contador_dedos.modes` faz um card aparecer aqui sozinho.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2

from .theme import (
    CARD_GAP,
    CARD_HEIGHT,
    CARD_WIDTH,
    CARDS_PER_ROW,
    COLOR_MUTED,
    COLOR_TEXT,
)
from .widgets import Rect, draw_card, draw_centered_text, draw_veil, hit_test, hud_scale

TITLE = "Contador de Dedos"
SUBTITLE = "Escolha o que deseja fazer"

#: Identificador da entrada que encerra o app.
QUIT_KEY = "quit"


@dataclass(frozen=True)
class MenuEntry:
    """Um card do menu.

    Attributes:
        key: identificador lógico devolvido na seleção.
        shortcut: a tecla que abre esta entrada, exibida no card.
        label: o texto do card.
    """

    key: str
    shortcut: str
    label: str


class Menu:
    """Tela de menu. Segue o mesmo contrato de um modo: ``process``/``on_mouse``."""

    name = "Menu"
    icon = "👋"
    hint = "Clique em um card  •  Q encerra"

    def __init__(self, entries: list[MenuEntry]) -> None:
        if not entries:
            raise ValueError("O menu precisa de pelo menos uma entrada.")
        self.entries = entries
        self.hovered: int | None = None
        self._selection: str | None = None
        self._rects: list[Rect] = []

    # -- layout -------------------------------------------------------------

    def layout(self, width: int, height: int) -> list[Rect]:
        """Distribui os cards em uma grade centralizada."""
        scale = hud_scale(height)
        card_w, card_h = int(CARD_WIDTH * scale), int(CARD_HEIGHT * scale)
        gap = int(CARD_GAP * scale)

        rects: list[Rect] = []
        rows = [
            self.entries[i : i + CARDS_PER_ROW] for i in range(0, len(self.entries), CARDS_PER_ROW)
        ]
        grid_height = len(rows) * card_h + (len(rows) - 1) * gap
        top = (height - grid_height) // 2 + int(20 * scale)

        for row_index, row in enumerate(rows):
            row_width = len(row) * card_w + (len(row) - 1) * gap
            left = (width - row_width) // 2
            y = top + row_index * (card_h + gap)
            for column in range(len(row)):
                rects.append(Rect(left + column * (card_w + gap), y, card_w, card_h))
        return rects

    # -- contrato de tela ---------------------------------------------------

    def process(self, frame, timestamp_ms: int = 0):
        height, width = frame.shape[:2]
        scale = hud_scale(height)
        draw_veil(frame)

        self._rects = self.layout(width, height)
        top = self._rects[0].y

        center_x = width // 2
        draw_centered_text(
            frame,
            TITLE,
            center_x,
            top - int(58 * scale),
            1.0 * scale,
            COLOR_TEXT,
            max(2, int(2 * scale)),
        )
        draw_centered_text(
            frame,
            SUBTITLE,
            center_x,
            top - int(28 * scale),
            0.5 * scale,
            COLOR_MUTED,
            max(1, int(scale)),
        )

        for index, (rect, entry) in enumerate(zip(self._rects, self.entries)):
            hovered = index == self.hovered
            draw_card(frame, rect, entry.shortcut, entry.label, scale, hovered=hovered)
        return frame

    def on_mouse(self, event: int, x: int, y: int) -> None:
        self.hovered = hit_test(self._rects, x, y)
        if event == cv2.EVENT_LBUTTONDOWN and self.hovered is not None:
            self._selection = self.entries[self.hovered].key

    def close(self) -> None:
        """O menu não segura recurso nenhum."""

    # -- seleção ------------------------------------------------------------

    def select_shortcut(self, shortcut: str) -> bool:
        """Seleciona pela tecla de atalho. Devolve se alguma entrada casou."""
        for entry in self.entries:
            if entry.shortcut.upper() == shortcut.upper():
                self._selection = entry.key
                return True
        return False

    def take_selection(self) -> str | None:
        """Devolve a escolha pendente e a consome.

        O `App` colhe a seleção no loop, e não dentro do callback do mouse, para
        que a troca de tela aconteça sempre no mesmo ponto do ciclo.
        """
        selection, self._selection = self._selection, None
        return selection
