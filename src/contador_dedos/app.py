"""Orquestrador: abre a câmera, roteia os frames para a tela atual e renderiza.

O loop não sabe nada sobre contar dedos — ele conhece apenas o contrato
:class:`~contador_dedos.modes.base.Mode`. É o que torna barato acrescentar o
menu (Fase 4) e as features seguintes.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

import cv2

from .config import AppConfig, parse_args
from .core.camera import Camera, CameraError
from .core.overlay import draw_status_bar
from .core.pipeline import FpsMeter, VideoClock
from .modes import Mode, build_modes, close_modes
from .vision.model import ModelError

WINDOW_NAME = "Contador de Dedos"

#: Q ou ESC encerram. A Fase 4 fará o ESC voltar ao menu.
KEYS_QUIT = (ord("q"), ord("Q"), 27)


def should_quit(key: int) -> bool:
    """Diz se a tecla pressionada encerra o app."""
    return key in KEYS_QUIT


def window_was_closed(window: str = WINDOW_NAME) -> bool:
    """Detecta o fechamento da janela pelo botão do sistema."""
    try:
        return cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


class App:
    """O loop principal e o roteamento entre telas."""

    def __init__(self, config: AppConfig, modes: list[Mode]) -> None:
        if not modes:
            raise ValueError("O app precisa de pelo menos um modo registrado.")
        self.config = config
        self.modes = modes
        # Sem menu ainda: entra direto no primeiro modo registrado. A Fase 4
        # troca esta linha pela tela de menu, e o resto do loop segue igual.
        self.screen: Mode = modes[0]
        self.running = True

    def handle_key(self, key: int) -> None:
        if should_quit(key):
            self.running = False

    def run(self) -> None:
        """Captura → detecção → anotação → render, até o usuário sair."""
        clock = VideoClock()
        fps_meter = FpsMeter()

        with Camera(self.config.camera_index, mirror=self.config.mirror) as camera:
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
            try:
                while self.running:
                    frame = camera.read()
                    if frame is None:
                        continue

                    frame = self.screen.process(frame, clock.tick())
                    draw_status_bar(frame, self.screen.hint, fps_meter.tick())

                    cv2.imshow(WINDOW_NAME, frame)
                    self.handle_key(cv2.waitKey(1) & 0xFF)
                    if window_was_closed():
                        self.running = False
            finally:
                cv2.destroyAllWindows()


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada: devolve 0 em caso de sucesso, 1 em caso de erro."""
    config = parse_args(argv)
    modes: list[Mode] = []
    try:
        modes = build_modes(config)
        App(config, modes).run()
    except (CameraError, ModelError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    finally:
        close_modes(modes)
    return 0
