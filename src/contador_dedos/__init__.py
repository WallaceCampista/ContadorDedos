"""Contador de Dedos — conta dedos levantados em tempo real usando a webcam.

A fachada pública do pacote. O entry point `contador-dedos` aponta para
:func:`main`, então ele continua estável mesmo quando a estrutura interna muda.
"""

from __future__ import annotations

from .app import App, main
from .config import AppConfig

__version__ = "0.4.0"
__all__ = ["App", "AppConfig", "__version__", "main"]
