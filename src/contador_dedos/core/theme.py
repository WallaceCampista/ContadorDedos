"""Paleta e tipografia — um só lugar para mexer na aparência.

A Fase 4 expande isto em `ui/theme.py`; por ora concentra o que o HUD usa.
"""

from __future__ import annotations

import cv2

FONT = cv2.FONT_HERSHEY_SIMPLEX

# Cores em BGR (a convenção do OpenCV).
COLOR_TEXT = (255, 255, 255)
COLOR_OUTLINE = (0, 0, 0)
COLOR_TOTAL = (0, 0, 255)
COLOR_HINT = (200, 200, 200)

#: Altura de referência para a qual os tamanhos do HUD foram desenhados.
HUD_REFERENCE_HEIGHT = 480
#: Piso da escala, para o texto não sumir em câmeras de baixa resolução.
MIN_HUD_SCALE = 0.5
