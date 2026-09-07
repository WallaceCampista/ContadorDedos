"""Testes da camada de desenho — rodam sem janela, direto sobre o array."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from contador_dedos.core.overlay import draw_status_bar, draw_text, hud_scale
from contador_dedos.core.theme import COLOR_TOTAL, HUD_REFERENCE_HEIGHT, MIN_HUD_SCALE
from contador_dedos.modes.finger_counter import draw_counters
from contador_dedos.vision.landmarks import landmarks_to_pixels

RESOLUCOES = [(320, 240), (640, 480), (1920, 1080)]


def frame(width: int = 640, height: int = 480, tom: int = 0) -> np.ndarray:
    return np.full((height, width, 3), tom, dtype=np.uint8)


def test_escala_e_neutra_na_altura_de_referencia():
    assert hud_scale(HUD_REFERENCE_HEIGHT) == 1.0


def test_escala_acompanha_a_resolucao():
    assert hud_scale(1080) == pytest.approx(2.25)


def test_escala_tem_piso_para_cameras_minusculas():
    """Sem o piso, uma câmera pequena zeraria o tamanho da fonte."""
    assert hud_scale(60) == MIN_HUD_SCALE
    assert hud_scale(1) == MIN_HUD_SCALE


@pytest.mark.parametrize("tom", [0, 255])
def test_texto_permanece_visivel_em_qualquer_fundo(tom):
    """O contorno é o que impede o texto de sumir em cenas claras ou escuras."""
    img = frame(tom=tom)
    draw_text(img, "teste", (10, 30))
    assert (img != tom).any()


@pytest.mark.parametrize("espelhado", [True, False])
def test_contadores_desenham_os_tres_paineis(espelhado):
    img = frame()
    draw_counters(img, {"Left": 2, "Right": 3}, espelhado)
    assert img.any()
    # O total é o único elemento vermelho do HUD.
    assert (img == np.array(COLOR_TOTAL, dtype=np.uint8)).all(axis=2).any()


@pytest.mark.parametrize(("width", "height"), RESOLUCOES)
def test_contadores_ocupam_os_dois_lados_do_topo(width, height):
    """Desenhar fora do array não levanta erro no OpenCV — precisa ser conferido."""
    img = frame(width, height)
    draw_counters(img, {"Left": 5, "Right": 5}, True)
    colunas = img.any(axis=(0, 2))
    linhas = img.any(axis=(1, 2))
    assert colunas[: width // 3].any(), "nada desenhado à esquerda"
    assert colunas[-width // 3 :].any(), "nada desenhado à direita"
    assert linhas[: height // 4].any(), "contadores ausentes no topo"
    assert not linhas[height // 2 :].any(), "contadores invadiram a metade de baixo"


def test_contadores_aceitam_mao_ausente():
    img = frame()
    draw_counters(img, {"Left": None, "Right": None}, True)
    assert img.any()  # mostra "-" em vez de um número


@pytest.mark.parametrize(("width", "height"), RESOLUCOES)
def test_barra_de_status_fica_no_rodape(width, height):
    img = frame(width, height)
    draw_status_bar(img, "Q ou ESC para sair", 12.3)
    linhas = img.any(axis=(1, 2))
    assert linhas[-height // 8 :].any(), "rodapé ausente"
    assert not linhas[: height // 2].any(), "rodapé invadiu a metade de cima"


def test_barra_de_status_mostra_fps_e_dica():
    """Os dois textos ficam em cantos opostos."""
    img = frame()
    draw_status_bar(img, "Q ou ESC para sair", 30.0)
    colunas = img.any(axis=(0, 2))
    assert colunas[:200].any(), "FPS ausente à esquerda"
    assert colunas[-200:].any(), "dica ausente à direita"


def test_landmarks_para_pixels():
    landmarks = [SimpleNamespace(x=0.0, y=0.0), SimpleNamespace(x=0.5, y=0.25)]
    assert landmarks_to_pixels(landmarks, 640, 480) == [(0, 0), (320, 120)]


def test_landmarks_para_pixels_preserva_a_ordem():
    landmarks = [SimpleNamespace(x=i / 21, y=i / 21) for i in range(21)]
    pixels = landmarks_to_pixels(landmarks, 210, 210)
    assert len(pixels) == 21
    assert pixels == sorted(pixels)
