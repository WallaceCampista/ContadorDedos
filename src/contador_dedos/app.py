"""Orquestrador: abre a câmera, roteia os frames para a tela atual e renderiza.

O loop não sabe nada sobre contar dedos — ele conhece apenas o contrato
:class:`~contador_dedos.modes.base.Mode`, que a tela de menu também cumpre.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

import cv2

from .config import AppConfig, parse_args
from .core.camera import Camera, CameraError
from .core.pipeline import FpsMeter, VideoClock
from .modes import Mode, build_modes, close_modes
from .ui.menu import QUIT_KEY, Menu, MenuEntry
from .ui.widgets import Rect, draw_status_bar
from .vision.model import ModelError

WINDOW_NAME = "Contador de Dedos"

#: Encerra o app de qualquer tela.
KEYS_QUIT = (ord("q"), ord("Q"))
#: Volta ao menu; no próprio menu, não faz nada.
KEY_BACK = 27  # ESC

BACK_LABEL = "← Voltar"
#: Prefixo dos identificadores de modo nas entradas do menu.
MODE_PREFIX = "mode:"


def is_printable(key: int) -> bool:
    """Filtra os códigos que não são caractere.

    Sem isto, o 255 que o `waitKey` devolve quando nenhuma tecla foi pressionada
    entraria como atalho do menu a cada frame.
    """
    return 32 <= key < 127


def should_quit(key: int) -> bool:
    """Diz se a tecla pressionada encerra o app."""
    return key in KEYS_QUIT


def window_was_closed(window: str = WINDOW_NAME) -> bool:
    """Detecta o fechamento da janela pelo botão do sistema."""
    try:
        return cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def build_menu(modes: Sequence[Mode]) -> Menu:
    """Monta o menu a partir dos modos registrados, mais a saída.

    Os atalhos numéricos seguem a ordem do registro, então acrescentar um modo
    faz surgir um card novo — sem tocar nesta função.
    """
    entries = [
        MenuEntry(key=f"{MODE_PREFIX}{index}", shortcut=str(index + 1), label=mode.name)
        for index, mode in enumerate(modes)
    ]
    entries.append(MenuEntry(key=QUIT_KEY, shortcut="Q", label="Sair"))
    return Menu(entries)


class App:
    """O loop principal e o roteamento entre o menu e os modos."""

    def __init__(self, config: AppConfig, modes: list[Mode]) -> None:
        if not modes:
            raise ValueError("O app precisa de pelo menos um modo registrado.")
        self.config = config
        self.modes = modes
        self.menu = build_menu(modes)
        self.screen: Mode | Menu = self.menu
        self.running = True
        self._back_rect: Rect | None = None
        self._back_hovered = False
        self._back_requested = False

    # -- navegação ----------------------------------------------------------

    @property
    def in_menu(self) -> bool:
        return self.screen is self.menu

    def show_menu(self) -> None:
        self.screen = self.menu
        self._back_hovered = False

    def open_mode(self, index: int) -> None:
        if 0 <= index < len(self.modes):
            self.screen = self.modes[index]

    def apply_selection(self, selection: str | None) -> None:
        """Executa a escolha feita no menu (por clique ou por tecla)."""
        if selection is None:
            return
        if selection == QUIT_KEY:
            self.running = False
        elif selection.startswith(MODE_PREFIX):
            self.open_mode(int(selection[len(MODE_PREFIX) :]))

    # -- entrada ------------------------------------------------------------

    def handle_key(self, key: int) -> None:
        if should_quit(key):
            self.running = False
        elif key == KEY_BACK:
            if not self.in_menu:
                self.show_menu()
        elif self.in_menu and is_printable(key):
            self.menu.select_shortcut(chr(key))

    def on_mouse(self, event: int, x: int, y: int, *_) -> None:
        """Callback do OpenCV. Só registra intenção; o loop é quem age."""
        if not self.in_menu and self._back_rect is not None:
            self._back_hovered = self._back_rect.contains(x, y)
            if self._back_hovered and event == cv2.EVENT_LBUTTONDOWN:
                self._back_requested = True
                return
        self.screen.on_mouse(event, x, y)

    # -- loop ---------------------------------------------------------------

    def run(self) -> None:
        """Captura → tela atual → moldura → render, até o usuário sair."""
        clock = VideoClock()
        fps_meter = FpsMeter()

        with Camera(self.config.camera_index, mirror=self.config.mirror) as camera:
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
            cv2.setMouseCallback(WINDOW_NAME, self.on_mouse)
            try:
                while self.running:
                    frame = camera.read()
                    if frame is None:
                        continue

                    frame = self.screen.process(frame, clock.tick())
                    self._back_rect = draw_status_bar(
                        frame,
                        self.screen.hint,
                        fps_meter.tick(),
                        back_label=None if self.in_menu else BACK_LABEL,
                        back_hovered=self._back_hovered,
                    )

                    cv2.imshow(WINDOW_NAME, frame)
                    self.handle_key(cv2.waitKey(1) & 0xFF)

                    if self._back_requested:
                        self._back_requested = False
                        self.show_menu()
                    self.apply_selection(self.menu.take_selection())

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
