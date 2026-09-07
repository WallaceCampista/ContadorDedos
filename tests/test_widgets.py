"""Testes das primitivas de interface: geometria, hit-testing e desenho."""

from __future__ import annotations

import numpy as np
import pytest

from contador_dedos.ui.theme import COLOR_PANEL
from contador_dedos.ui.widgets import (
    Rect,
    draw_card,
    draw_panel,
    draw_text,
    draw_veil,
    hit_test,
    text_size,
)


def frame(width: int = 640, height: int = 480, tom: int = 255) -> np.ndarray:
    return np.full((height, width, 3), tom, dtype=np.uint8)


def test_rect_calcula_bordas_e_centro():
    rect = Rect(10, 20, 100, 50)
    assert (rect.right, rect.bottom) == (110, 70)
    assert rect.center == (60, 45)


@pytest.mark.parametrize(
    ("ponto", "dentro"),
    [
        ((60, 45), True),  # centro
        ((10, 20), True),  # canto superior esquerdo (borda conta)
        ((110, 70), True),  # canto inferior direito
        ((9, 45), False),
        ((111, 45), False),
        ((60, 19), False),
        ((60, 71), False),
    ],
)
def test_rect_contains(ponto, dentro):
    assert Rect(10, 20, 100, 50).contains(*ponto) is dentro


def test_hit_test_devolve_o_indice():
    rects = [Rect(0, 0, 10, 10), Rect(20, 0, 10, 10), Rect(40, 0, 10, 10)]
    assert hit_test(rects, 5, 5) == 0
    assert hit_test(rects, 25, 5) == 1
    assert hit_test(rects, 45, 5) == 2


def test_hit_test_fora_de_tudo_devolve_none():
    assert hit_test([Rect(0, 0, 10, 10)], 50, 50) is None
    assert hit_test([], 0, 0) is None


def test_painel_escurece_a_regiao_indicada():
    img = frame()
    draw_panel(img, Rect(10, 10, 100, 40))
    assert img[30, 50, 0] < 255, "a região do painel precisa escurecer"
    assert img[100, 50, 0] == 255, "fora do painel nada muda"


def test_painel_fora_da_tela_nao_quebra():
    """Um layout mal calculado não pode derrubar o app."""
    img = frame()
    draw_panel(img, Rect(-50, -50, 20, 20))
    draw_panel(img, Rect(10_000, 10_000, 50, 50))
    assert (img == 255).all(), "nada deveria ter sido pintado"


def test_veu_escurece_o_frame_inteiro():
    img = frame()
    draw_veil(img)
    assert (img < 255).all()


def test_texto_nao_deixa_rastro_de_contorno():
    """O contorno usa a mesma espessura do preenchimento.

    Com um traço mais grosso por baixo, o glifo do OpenCV fica mais largo e o
    contorno termina alguns pixels à direita — um rastro escuro visível.
    """
    texto = "Escolha o que deseja fazer"
    escala, espessura = 1.0, 1
    largura, _ = text_size(texto, escala, espessura)

    img = frame(width=largura + 200, tom=255)
    draw_text(img, texto, (20, 100), escala, (255, 255, 255), espessura)

    escuro = (img.max(axis=2) < 128).any(axis=0)
    ultima_coluna_escura = int(np.flatnonzero(escuro).max())
    folga = ultima_coluna_escura - (20 + largura)
    assert folga <= 3, f"o contorno vazou {folga}px além do texto"


def test_card_destacado_difere_do_normal():
    normal, destacado = frame(tom=0), frame(tom=0)
    rect = Rect(50, 50, 190, 132)
    draw_card(normal, rect, "1", "Contar Dedos", 1.0, hovered=False)
    draw_card(destacado, rect, "1", "Contar Dedos", 1.0, hovered=True)
    assert (normal != destacado).any(), "o hover precisa ser visível"


def test_card_desenha_dentro_da_sua_area():
    img = frame(tom=0)
    rect = Rect(50, 50, 190, 132)
    draw_card(img, rect, "1", "Contar Dedos", 1.0)
    pintado = img.any(axis=2)
    assert not pintado[: rect.y - 1].any(), "vazou para cima"
    assert not pintado[rect.bottom + 2 :].any(), "vazou para baixo"
    assert not pintado[:, : rect.x - 1].any(), "vazou para a esquerda"
    assert not pintado[:, rect.right + 2 :].any(), "vazou para a direita"


def test_cor_do_painel_e_escura():
    """O tema assume painel escuro com texto claro — o contraste depende disso."""
    assert max(COLOR_PANEL) < 80
