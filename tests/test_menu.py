"""Testes da tela de menu: layout, hover, clique e atalhos."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from contador_dedos.ui.menu import QUIT_KEY, Menu, MenuEntry

ENTRADAS = [
    MenuEntry(key="mode:0", shortcut="1", label="Contar Dedos"),
    MenuEntry(key="mode:1", shortcut="2", label="Gestos"),
    MenuEntry(key=QUIT_KEY, shortcut="Q", label="Sair"),
]


@pytest.fixture
def menu() -> Menu:
    return Menu(list(ENTRADAS))


def frame(width: int = 640, height: int = 480) -> np.ndarray:
    return np.full((height, width, 3), 200, dtype=np.uint8)


def test_menu_vazio_e_recusado():
    with pytest.raises(ValueError, match="pelo menos uma entrada"):
        Menu([])


def test_layout_cria_um_card_por_entrada(menu):
    assert len(menu.layout(640, 480)) == len(ENTRADAS)


def test_cards_nao_se_sobrepoem(menu):
    rects = menu.layout(1280, 720)
    for i, a in enumerate(rects):
        for b in rects[i + 1 :]:
            separados = a.right < b.x or b.right < a.x or a.bottom < b.y or b.bottom < a.y
            assert separados, "dois cards se sobrepõem"


@pytest.mark.parametrize(("width", "height"), [(320, 240), (640, 480), (1920, 1080)])
def test_cards_cabem_na_tela(menu, width, height):
    for rect in menu.layout(width, height):
        assert rect.x >= 0 and rect.right <= width
        assert rect.y >= 0 and rect.bottom <= height


def test_grade_quebra_linha_depois_de_tres_cards():
    muitos = [MenuEntry(f"m{i}", str(i), f"Modo {i}") for i in range(5)]
    rects = Menu(muitos).layout(1280, 720)
    linhas = {rect.y for rect in rects}
    assert len(linhas) == 2, "5 cards deveriam ocupar duas linhas"


def test_hover_segue_o_mouse(menu):
    img = frame()
    menu.process(img)
    alvo = menu.layout(640, 480)[1]
    menu.on_mouse(cv2.EVENT_MOUSEMOVE, *alvo.center)
    assert menu.hovered == 1
    menu.on_mouse(cv2.EVENT_MOUSEMOVE, 0, 0)
    assert menu.hovered is None


def test_clique_em_card_seleciona(menu):
    menu.process(frame())
    alvo = menu.layout(640, 480)[0]
    menu.on_mouse(cv2.EVENT_LBUTTONDOWN, *alvo.center)
    assert menu.take_selection() == "mode:0"


def test_clique_fora_dos_cards_nao_seleciona(menu):
    menu.process(frame())
    menu.on_mouse(cv2.EVENT_LBUTTONDOWN, 5, 5)
    assert menu.take_selection() is None


def test_selecao_e_consumida_uma_vez_so(menu):
    menu.process(frame())
    menu.on_mouse(cv2.EVENT_LBUTTONDOWN, *menu.layout(640, 480)[2].center)
    assert menu.take_selection() == QUIT_KEY
    assert menu.take_selection() is None, "a seleção não pode disparar duas vezes"


def test_mover_o_mouse_nao_seleciona(menu):
    menu.process(frame())
    menu.on_mouse(cv2.EVENT_MOUSEMOVE, *menu.layout(640, 480)[0].center)
    assert menu.take_selection() is None


@pytest.mark.parametrize(("tecla", "esperado"), [("1", "mode:0"), ("2", "mode:1"), ("q", QUIT_KEY)])
def test_atalho_de_teclado_seleciona(menu, tecla, esperado):
    assert menu.select_shortcut(tecla) is True
    assert menu.take_selection() == esperado


def test_atalho_desconhecido_nao_seleciona(menu):
    assert menu.select_shortcut("z") is False
    assert menu.take_selection() is None


def test_process_desenha_e_devolve_o_frame(menu):
    img = frame()
    assert menu.process(img) is img
    assert (img != 200).any(), "o menu não desenhou nada"


def test_menu_escurece_a_webcam_ao_fundo(menu):
    """A cena continua visível, mas os cards precisam ganhar o primeiro plano."""
    img = frame()
    menu.process(img)
    canto = img[5, 5]
    assert (canto < 200).all(), "o véu não foi aplicado"
    assert (canto > 0).any(), "o véu não pode apagar a imagem"


def test_hover_muda_o_desenho(menu):
    normal, destacado = frame(), frame()
    menu.process(normal)
    menu.on_mouse(cv2.EVENT_MOUSEMOVE, *menu.layout(640, 480)[0].center)
    menu.process(destacado)
    assert (normal != destacado).any()
