"""Orquestrador: abre a câmera, roteia os frames para a tela atual e renderiza.

O loop não sabe nada sobre contar dedos — ele conhece apenas o contrato
:class:`~contador_dedos.modes.base.Mode`, que a tela de menu também cumpre.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

import cv2

from .config import AppConfig, parse_args
from .core import audio
from .core.camera import Camera, CameraError
from .core.pipeline import FpsMeter, VideoClock
from .core.recorder import Recorder, RecorderError
from .i18n import set_language, t
from .modes import Mode, build_hand_tracker, build_modes, close_modes
from .ui.menu import QUIT_KEY, Menu, MenuEntry
from .ui.theme import COLOR_ACCENT, COLOR_RECORDING
from .ui.widgets import (
    Rect,
    draw_centered_text,
    draw_status_bar,
    draw_text,
    hud_scale,
    text_size,
)
from .vision.model import ModelError

WINDOW_NAME = "Contador de Dedos"

#: Encerra o app de qualquer tela.
KEYS_QUIT = (ord("q"), ord("Q"))
#: Volta ao menu; no próprio menu, não faz nada.
KEY_BACK = 27  # ESC
#: Salva um PNG do que está na tela.
KEY_SNAPSHOT = ord("s")
#: Liga/desliga a gravação de vídeo.
KEY_RECORD = ord("r")
#: Por quantos frames um aviso do app fica na tela.
NOTICE_FRAMES = 60

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
        self.recorder = Recorder(config.output_dir)
        self._notice: str | None = None
        self._notice_frames = 0
        self._snapshot_requested = False
        self._record_requested = False

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
        # A tela corrente tem a primeira chance: um campo de texto precisa
        # receber o "q" como letra, e não como "encerrar o app".
        if self.screen.on_key(key):
            return
        if should_quit(key):
            self.running = False
        elif key == KEY_BACK:
            if not self.in_menu:
                self.show_menu()
        elif key == KEY_SNAPSHOT:
            self._snapshot_requested = True
        elif key == KEY_RECORD:
            self._record_requested = True
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

    # -- captura ------------------------------------------------------------

    def notify(self, message: str) -> None:
        self._notice, self._notice_frames = message, NOTICE_FRAMES

    def _apply_capture(self, frame) -> None:
        """Executa os pedidos de snapshot e gravação feitos pelo teclado."""
        if self._snapshot_requested:
            self._snapshot_requested = False
            try:
                caminho = self.recorder.snapshot(frame)
            except (RecorderError, OSError) as error:
                self.notify(str(error))
            else:
                self.notify(f"{t('Snapshot salvo')}: {caminho.name}")

        if self._record_requested:
            self._record_requested = False
            gravava = self.recorder.is_recording
            try:
                caminho = self.recorder.toggle(frame)
            except (RecorderError, OSError) as error:
                self.notify(f"{t('Não consegui gravar o vídeo')}: {error}")
            else:
                if gravava and caminho is not None:
                    self.notify(f"{t('Vídeo salvo')}: {caminho.name}")

    def _draw_overlays(self, frame) -> None:
        """Indicador de gravação e aviso temporário, por cima de tudo.

        Desenhados **depois** de o frame ir para o vídeo: o arquivo gravado sai
        limpo, sem o próprio indicador de REC queimado em cima.
        """
        height, width = frame.shape[:2]
        scale = hud_scale(height)
        if self.recorder.is_recording:
            segundos = int(self.recorder.elapsed)
            rotulo = f"{t('Gravando')} {segundos // 60:02d}:{segundos % 60:02d}"
            largura = text_size(rotulo, 0.5 * scale, max(1, int(scale)))[0]
            x, y = width - largura - int(16 * scale), int(120 * scale)
            cv2.circle(
                frame,
                (x - int(12 * scale), y - int(5 * scale)),
                max(4, int(5 * scale)),
                COLOR_RECORDING,
                -1,
                cv2.LINE_AA,
            )
            draw_text(frame, rotulo, (x, y), 0.5 * scale, COLOR_RECORDING, max(1, int(scale)))

        if self._notice is None:
            return
        self._notice_frames -= 1
        if self._notice_frames <= 0:
            self._notice = None
            return
        draw_centered_text(
            frame, self._notice, width // 2, height - int(52 * scale), 0.45 * scale, COLOR_ACCENT
        )

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
                        t(self.screen.hint),
                        fps_meter.tick(),
                        back_label=None if self.in_menu else t(BACK_LABEL),
                        back_hovered=self._back_hovered,
                    )

                    self._apply_capture(frame)
                    self.recorder.write(frame)
                    self._draw_overlays(frame)

                    cv2.imshow(WINDOW_NAME, frame)
                    self.handle_key(cv2.waitKey(1) & 0xFF)

                    if self._back_requested:
                        self._back_requested = False
                        self.show_menu()
                    self.apply_selection(self.menu.take_selection())

                    if window_was_closed():
                        self.running = False
            finally:
                self.recorder.close()
                cv2.destroyAllWindows()


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada: devolve 0 em caso de sucesso, 1 em caso de erro."""
    config = parse_args(argv)
    set_language(config.language)
    audio.configure(config.sound)
    try:
        with build_hand_tracker(config) as tracker:
            modes = build_modes(config, tracker)
            try:
                App(config, modes).run()
            finally:
                close_modes(modes)
    except (CameraError, ModelError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    finally:
        audio.close()
    return 0
