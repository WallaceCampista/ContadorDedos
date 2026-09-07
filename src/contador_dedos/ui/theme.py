"""Tokens visuais — o único lugar para mexer na aparência do app.

Cores em **BGR**, a convenção do OpenCV.

Uma limitação da HighGUI moldou este tema: `cv2.putText` usa fontes Hershey, que
renderizam acentos e setas (`←`) mas **não emoji**. Por isso os cards do menu
usam a própria tecla de atalho como âncora visual, em vez de um ícone.
"""

from __future__ import annotations

import cv2

FONT = cv2.FONT_HERSHEY_SIMPLEX

# --- Texto ---
COLOR_TEXT = (255, 255, 255)
COLOR_OUTLINE = (0, 0, 0)
COLOR_HINT = (200, 200, 200)
COLOR_MUTED = (160, 158, 155)
COLOR_TOTAL = (0, 0, 255)
#: Vermelho do indicador de gravação.
COLOR_RECORDING = (60, 60, 255)

# --- Superfícies ---
COLOR_PANEL = (26, 24, 22)
COLOR_CARD = (52, 47, 43)
COLOR_CARD_HOVER = (84, 76, 68)
COLOR_BORDER = (92, 88, 84)
#: Âmbar — o realce de foco (hover, tecla de atalho).
COLOR_ACCENT = (0, 170, 255)

# --- Transparências ---
#: Véu sobre a webcam no menu: deixa a cena visível sem competir com os cards.
VEIL_ALPHA = 0.62
#: Faixas atrás do HUD, para o texto não sumir em cenas claras.
PANEL_ALPHA = 0.55
CARD_ALPHA = 0.88

# --- Métricas ---
#: Altura de referência para a qual os tamanhos foram desenhados.
HUD_REFERENCE_HEIGHT = 480
#: Piso da escala, para o texto não sumir em câmeras de baixa resolução.
MIN_HUD_SCALE = 0.5

#: Tamanho do card do menu, em pixels da altura de referência.
CARD_WIDTH = 190
CARD_HEIGHT = 132
CARD_GAP = 22
#: Máximo de cards por linha antes de quebrar para a linha de baixo.
CARDS_PER_ROW = 3
