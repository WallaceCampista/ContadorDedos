"""Primitivas de interface desenhadas sobre o frame: texto, painéis e cards.

A HighGUI não tem widgets — botão é retângulo desenhado, e clique é
`hit_test` sobre a área desse retângulo. Concentrar isso aqui é o que permitirá
trocar por PySide6 depois mexendo só na camada `ui/`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import cv2

from ..i18n import t
from .theme import (
    CARD_ALPHA,
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_CARD_HOVER,
    COLOR_HINT,
    COLOR_MUTED,
    COLOR_OUTLINE,
    COLOR_PANEL,
    COLOR_TEXT,
    FONT,
    HUD_REFERENCE_HEIGHT,
    MIN_HUD_SCALE,
    PANEL_ALPHA,
    VEIL_ALPHA,
)

#: Mostrado no lugar de um valor que não pôde ser lido.
UNKNOWN_VALUE = "—"


@dataclass(frozen=True)
class Rect:
    """Uma área retangular na imagem, em pixels."""

    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2

    def contains(self, x: int, y: int) -> bool:
        """A borda conta como dentro — é o que o usuário espera ao clicar nela."""
        return self.x <= x <= self.right and self.y <= y <= self.bottom


def hit_test(rects: Sequence[Rect], x: int, y: int) -> int | None:
    """Índice do primeiro retângulo que contém o ponto, ou ``None``."""
    for index, rect in enumerate(rects):
        if rect.contains(x, y):
            return index
    return None


def hud_scale(height: int) -> float:
    """Fator de escala da interface, para caber em qualquer resolução.

    Os tamanhos foram desenhados para 480px de altura; em uma webcam 1080p a
    interface sem escala vira um detalhe ilegível no canto.
    """
    return max(height / HUD_REFERENCE_HEIGHT, MIN_HUD_SCALE)


def text_size(text: str, scale: float, thickness: int = 1) -> tuple[int, int]:
    (width, height), _ = cv2.getTextSize(text, FONT, scale, thickness)
    return width, height


#: Deslocamentos do contorno, nas 8 direções ao redor do texto.
_OUTLINE_OFFSETS = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))


def draw_text(
    img,
    text: str,
    org: tuple[int, int],
    scale: float = 0.6,
    color: tuple[int, int, int] = COLOR_TEXT,
    thickness: int = 1,
) -> None:
    """Escreve com contorno preto, para o texto não sumir em fundos claros.

    O contorno é feito repetindo o texto deslocado ao redor, e **não** com um
    traço mais grosso por baixo: no OpenCV a largura do glifo cresce junto com a
    espessura, então o traço grosso terminaria alguns pixels à direita do
    preenchimento — um rastro escuro visível em textos longos.
    """
    x, y = org
    step = max(1, (thickness + 1) // 2)
    for dx, dy in _OUTLINE_OFFSETS:
        cv2.putText(
            img,
            text,
            (x + dx * step, y + dy * step),
            FONT,
            scale,
            COLOR_OUTLINE,
            thickness,
            cv2.LINE_AA,
        )
    cv2.putText(img, text, org, FONT, scale, color, thickness, cv2.LINE_AA)


def draw_centered_text(
    img,
    text: str,
    center_x: int,
    baseline_y: int,
    scale: float,
    color: tuple[int, int, int] = COLOR_TEXT,
    thickness: int = 1,
) -> None:
    """Como :func:`draw_text`, mas centralizando horizontalmente em ``center_x``."""
    width, _ = text_size(text, scale, thickness)
    draw_text(img, text, (center_x - width // 2, baseline_y), scale, color, thickness)


def draw_center_message(img, text: str, scale: float) -> None:
    """Mensagem no centro da tela — o estado vazio de um modo.

    Dizer "nenhuma mão detectada" evita a ambiguidade de um zero, que tanto
    pode significar "punho fechado" quanto "não estou vendo nada".
    """
    height, width = img.shape[:2]
    draw_centered_text(
        img, text, width // 2, height // 2, 0.6 * scale, COLOR_MUTED, max(1, int(scale))
    )


def draw_panel(
    img,
    rect: Rect,
    color: tuple[int, int, int] = COLOR_PANEL,
    alpha: float = PANEL_ALPHA,
) -> None:
    """Pinta um retângulo semitransparente sobre o frame.

    É o que dá legibilidade ao texto sobre uma cena qualquer — sem isso, o HUD
    branco desaparece contra uma parede clara.
    """
    x0, y0 = max(rect.x, 0), max(rect.y, 0)
    x1, y1 = min(rect.right, img.shape[1]), min(rect.bottom, img.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    region = img[y0:y1, x0:x1]
    overlay = region.copy()
    overlay[:] = color
    cv2.addWeighted(overlay, alpha, region, 1 - alpha, 0, dst=region)


def draw_veil(img, alpha: float = VEIL_ALPHA) -> None:
    """Escurece o frame inteiro — usado pelo menu, que não é sobre a imagem."""
    draw_panel(img, Rect(0, 0, img.shape[1], img.shape[0]), alpha=alpha)


def draw_card(
    img,
    rect: Rect,
    shortcut: str,
    label: str,
    scale: float,
    hovered: bool = False,
) -> None:
    """Desenha um card do menu.

    A tecla de atalho é a âncora visual do card (as fontes da HighGUI não
    renderizam emoji) e ao mesmo tempo documenta o caminho pelo teclado.
    """
    draw_panel(img, rect, COLOR_CARD_HOVER if hovered else COLOR_CARD, CARD_ALPHA)
    cv2.rectangle(
        img,
        (rect.x, rect.y),
        (rect.right, rect.bottom),
        COLOR_ACCENT if hovered else COLOR_BORDER,
        max(2, int(2 * scale)) if hovered else max(1, int(scale)),
        cv2.LINE_AA,
    )

    center_x = rect.center[0]
    draw_centered_text(
        img,
        shortcut,
        center_x,
        rect.y + int(rect.height * 0.55),
        1.6 * scale,
        COLOR_ACCENT if hovered else COLOR_TEXT,
        max(2, int(3 * scale)),
    )
    draw_centered_text(
        img,
        label,
        center_x,
        rect.bottom - int(18 * scale),
        0.5 * scale,
        COLOR_TEXT if hovered else COLOR_MUTED,
        max(1, int(scale)),
    )


def draw_button(img, rect: Rect, text: str, scale: float, hovered: bool = False) -> None:
    """Botão pequeno da barra de status (o '← Voltar')."""
    draw_panel(img, rect, COLOR_CARD_HOVER if hovered else COLOR_CARD, CARD_ALPHA)
    cv2.rectangle(
        img,
        (rect.x, rect.y),
        (rect.right, rect.bottom),
        COLOR_ACCENT if hovered else COLOR_BORDER,
        max(1, int(scale)),
        cv2.LINE_AA,
    )
    width, height = text_size(text, 0.5 * scale, max(1, int(scale)))
    draw_text(
        img,
        text,
        (rect.center[0] - width // 2, rect.center[1] + height // 2),
        0.5 * scale,
        COLOR_ACCENT if hovered else COLOR_TEXT,
        max(1, int(scale)),
    )


def draw_hand_readout(
    img,
    values: dict[str, str | None],
    mirrored: bool = True,
    caption: str | None = None,
    empty_message: str | None = None,
) -> None:
    """Painel de duas colunas: o que foi lido em cada mão.

    Cada coluna fica do lado da tela em que aquela mão realmente aparece, e a
    da direita é alinhada pela borda — com deslocamento fixo, um valor mais
    longo vazaria para fora do frame.

    Args:
        values: o valor de cada mão, nas chaves ``"Left"``/``"Right"``.
        mirrored: se a imagem está espelhada (define de que lado cada mão está).
        caption: nota discreta abaixo dos valores, para limitações do modo.
        empty_message: mostrado no centro quando nenhuma mão foi lida.
    """
    height, width = img.shape[:2]
    scale = hud_scale(height)
    margin = int(10 * scale)
    label_scale, value_scale = 0.5 * scale, 0.8 * scale
    label_weight, value_weight = max(1, int(scale)), max(2, int(2 * scale))
    band_height = int((94 if caption else 76) * scale)
    draw_panel(img, Rect(0, 0, width, band_height))

    left_hand, right_hand = ("Left", "Right") if mirrored else ("Right", "Left")
    colunas = (
        (left_hand, t("Esquerda") if mirrored else t("Direita"), False),
        (right_hand, t("Direita") if mirrored else t("Esquerda"), True),
    )

    for hand, side_label, align_right in colunas:
        value = values[hand]
        shown = value or UNKNOWN_VALUE
        if align_right:
            label_x = width - margin - text_size(side_label, label_scale, label_weight)[0]
            value_x = width - margin - text_size(shown, value_scale, value_weight)[0]
        else:
            label_x = value_x = margin
        draw_text(
            img, side_label, (label_x, int(28 * scale)), label_scale, COLOR_MUTED, label_weight
        )
        draw_text(
            img,
            shown,
            (value_x, int(60 * scale)),
            value_scale,
            COLOR_ACCENT if value else COLOR_MUTED,
            value_weight,
        )

    if caption:
        draw_centered_text(
            img, caption, width // 2, band_height - int(10 * scale), 0.4 * scale, COLOR_MUTED
        )
    if empty_message and all(value is None for value in values.values()):
        draw_center_message(img, empty_message, scale)


def draw_status_bar(
    img,
    hint: str,
    fps: float,
    back_label: str | None = None,
    back_hovered: bool = False,
) -> Rect | None:
    """Rodapé comum a todas as telas.

    Da esquerda para a direita: o botão de voltar (quando há para onde voltar),
    a dica de atalhos e o FPS. Devolve a área do botão, para o `App` testar o
    clique — ``None`` quando não há botão.
    """
    height, width = img.shape[:2]
    scale = hud_scale(height)
    thickness = max(1, int(scale))
    band_height = int(34 * scale)
    band = Rect(0, height - band_height, width, band_height)
    draw_panel(img, band)

    baseline = band.bottom - int(11 * scale)
    margin = int(10 * scale)

    back_rect: Rect | None = None
    if back_label is not None:
        label_width, _ = text_size(back_label, 0.5 * scale, thickness)
        back_rect = Rect(
            margin,
            band.y + int(5 * scale),
            label_width + int(20 * scale),
            band_height - int(10 * scale),
        )
        draw_button(img, back_rect, back_label, scale, back_hovered)

    fps_text = f"{fps:4.1f} FPS"
    fps_width, _ = text_size(fps_text, 0.5 * scale, thickness)
    fps_org = (width - fps_width - margin, baseline)
    draw_text(img, fps_text, fps_org, 0.5 * scale, COLOR_HINT, thickness)

    hint_width, _ = text_size(hint, 0.5 * scale, thickness)
    hint_x = max((width - hint_width) // 2, (back_rect.right + margin) if back_rect else margin)
    draw_text(img, hint, (hint_x, baseline), 0.5 * scale, COLOR_HINT, thickness)

    return back_rect
