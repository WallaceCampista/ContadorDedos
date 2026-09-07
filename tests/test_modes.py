"""Testes do contrato `Mode`, do registro e do roteamento do `App`."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from contador_dedos.app import KEY_BACK, App, build_menu, should_quit
from contador_dedos.config import AppConfig
from contador_dedos.modes import MODE_FACTORIES, Mode, build_modes, close_modes
from contador_dedos.modes.face_id import FaceId
from contador_dedos.modes.finger_counter import FingerCounter
from contador_dedos.modes.gesture import GestureRecognizer
from contador_dedos.modes.libras import LibrasNumbers
from contador_dedos.ui.menu import QUIT_KEY
from contador_dedos.ui.widgets import Rect


class FakeMode(Mode):
    """Modo mínimo: registra o que recebeu, sem tocar em câmera ou modelo."""

    name = "Falso"
    icon = "🧪"
    hint = "dica"

    def __init__(self, falha_ao_fechar: bool = False):
        self.processados = []
        self.cliques = []
        self.fechado = False
        self._falha_ao_fechar = falha_ao_fechar

    def process(self, frame, timestamp_ms: int = 0):
        self.processados.append(timestamp_ms)
        return frame

    def on_mouse(self, event: int, x: int, y: int) -> None:
        self.cliques.append((event, x, y))

    def close(self) -> None:
        self.fechado = True
        if self._falha_ao_fechar:
            raise RuntimeError("boom")


def _frame(width: int = 640, height: int = 480) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


class _TrackerEspiao:
    """Detector de mentira: registra se alguém tentou fechá-lo."""

    def __init__(self):
        self.fechado = False

    def detect(self, frame, timestamp_ms):
        return []

    def close(self):
        self.fechado = True


def test_mode_e_abstrato():
    """Esquecer o `process` precisa falhar na hora, não em produção."""

    class SemProcess(Mode):
        pass

    with pytest.raises(TypeError, match="process"):
        SemProcess()


def test_mode_tem_ganchos_opcionais():
    """`on_mouse` e `close` são opcionais — a Fase 4 usa o primeiro."""
    modo = FakeMode()
    assert modo.on_mouse(0, 10, 20) is None
    assert Mode.on_mouse(modo, 0, 10, 20) is None  # o padrão da ABC não faz nada


def test_finger_counter_se_apresenta_para_o_menu():
    """O menu da Fase 4 monta os cards a partir destes atributos."""
    assert FingerCounter.name
    assert FingerCounter.icon
    assert issubclass(FingerCounter, Mode)


def test_registro_nao_esta_vazio():
    assert MODE_FACTORIES


def test_build_modes_repassa_config_e_detector(monkeypatch):
    recebidos = []

    def fabrica(config, tracker):
        recebidos.append((config, tracker))
        return FakeMode()

    monkeypatch.setattr("contador_dedos.modes.MODE_FACTORIES", (fabrica, fabrica))
    config, tracker = AppConfig(camera_index=3), object()
    modos = build_modes(config, tracker)
    assert len(modos) == 2
    assert recebidos == [(config, tracker), (config, tracker)]


def test_detector_e_um_so_para_todos_os_modos(monkeypatch):
    """Um detector por modo carregaria o mesmo modelo várias vezes."""
    trackers = []

    def fabrica(config, tracker):
        trackers.append(tracker)
        return FakeMode()

    monkeypatch.setattr("contador_dedos.modes.MODE_FACTORIES", (fabrica, fabrica, fabrica))
    build_modes(AppConfig(), object())
    assert len({id(t) for t in trackers}) == 1


@pytest.mark.parametrize("modo", [FingerCounter, GestureRecognizer, LibrasNumbers])
def test_modos_registrados_nao_fecham_o_detector_compartilhado(modo):
    """Fechar o detector em um modo derrubaria os outros."""
    tracker = _TrackerEspiao()
    instancia = modo.from_config(AppConfig(), tracker)
    instancia.close()
    assert tracker.fechado is False


def test_registro_traz_os_modos_de_visao():
    assert len(MODE_FACTORIES) == 4
    nomes = {FingerCounter.name, GestureRecognizer.name, LibrasNumbers.name, FaceId.name}
    assert nomes == {"Contar Dedos", "Gestos", "Libras", "Rosto (ID)"}


def test_close_modes_fecha_todos():
    modos = [FakeMode(), FakeMode()]
    close_modes(modos)
    assert all(modo.fechado for modo in modos)


def test_falha_ao_fechar_nao_impede_os_demais(capsys):
    """Cleanup não pode abortar: senão a câmera fica presa."""
    modos = [FakeMode(falha_ao_fechar=True), FakeMode()]
    close_modes(modos)
    assert modos[1].fechado
    assert "Falso" in capsys.readouterr().err


def test_app_exige_ao_menos_um_modo():
    with pytest.raises(ValueError, match="pelo menos um modo"):
        App(AppConfig(), [])


def test_app_abre_no_menu():
    app = App(AppConfig(), [FakeMode(), FakeMode()])
    assert app.in_menu
    assert app.screen is app.menu
    assert app.running is True


def test_menu_ganha_um_card_por_modo_mais_a_saida():
    """É isto que torna barato acrescentar uma feature: o card vem de graça."""
    menu = build_menu([FakeMode(), FakeMode()])
    assert [e.key for e in menu.entries] == ["mode:0", "mode:1", QUIT_KEY]
    assert [e.shortcut for e in menu.entries] == ["1", "2", "Q"]


def test_o_modo_de_gestos_aparece_no_menu():
    """O card do modo novo veio sem tocar na camada de UI."""
    modos = [FingerCounter(_TrackerEspiao()), GestureRecognizer(_TrackerEspiao())]
    menu = build_menu([*modos, LibrasNumbers(_TrackerEspiao())])
    assert [e.label for e in menu.entries] == ["Contar Dedos", "Gestos", "Libras", "Sair"]
    assert [e.shortcut for e in menu.entries] == ["1", "2", "3", "Q"]


@pytest.mark.parametrize("tecla", [ord("q"), ord("Q")])
def test_q_encerra_de_qualquer_tela(tecla):
    app = App(AppConfig(), [FakeMode()])
    app.handle_key(tecla)
    assert app.running is False

    app = App(AppConfig(), [FakeMode()])
    app.open_mode(0)
    app.handle_key(tecla)
    assert app.running is False


def test_esc_volta_ao_menu_sem_encerrar():
    app = App(AppConfig(), [FakeMode()])
    app.open_mode(0)
    assert not app.in_menu
    app.handle_key(KEY_BACK)
    assert app.in_menu
    assert app.running is True


def test_esc_no_menu_nao_faz_nada():
    app = App(AppConfig(), [FakeMode()])
    app.handle_key(KEY_BACK)
    assert app.in_menu
    assert app.running is True


@pytest.mark.parametrize("tecla", [ord("a"), 255, ord(" ")])
def test_outras_teclas_nao_param_o_loop(tecla):
    app = App(AppConfig(), [FakeMode()])
    app.handle_key(tecla)
    assert app.running is True
    assert should_quit(tecla) is False


def test_atalho_numerico_abre_o_modo():
    primeiro, segundo = FakeMode(), FakeMode()
    app = App(AppConfig(), [primeiro, segundo])
    app.handle_key(ord("2"))
    app.apply_selection(app.menu.take_selection())
    assert app.screen is segundo


def test_atalho_so_vale_dentro_do_menu():
    app = App(AppConfig(), [FakeMode(), FakeMode()])
    app.open_mode(0)
    app.handle_key(ord("2"))
    assert app.menu.take_selection() is None, "o modo não pode receber atalhos do menu"


def test_clique_no_card_abre_o_modo():
    primeiro = FakeMode()
    app = App(AppConfig(), [primeiro])
    app.screen.process(_frame())
    alvo = app.menu.layout(640, 480)[0]
    app.on_mouse(cv2.EVENT_LBUTTONDOWN, *alvo.center)
    app.apply_selection(app.menu.take_selection())
    assert app.screen is primeiro


def test_card_sair_encerra():
    app = App(AppConfig(), [FakeMode()])
    app.apply_selection(QUIT_KEY)
    assert app.running is False


def test_selecao_vazia_nao_muda_nada():
    app = App(AppConfig(), [FakeMode()])
    app.apply_selection(None)
    assert app.in_menu and app.running


def test_indice_de_modo_invalido_e_ignorado():
    app = App(AppConfig(), [FakeMode()])
    app.open_mode(9)
    assert app.in_menu, "um índice fora da faixa não pode trocar de tela"


def test_clique_no_voltar_pede_o_retorno_ao_menu():
    """O clique só registra a intenção; o loop é quem troca de tela."""
    app = App(AppConfig(), [FakeMode()])
    app.open_mode(0)
    app._back_rect = Rect(10, 400, 100, 30)
    app.on_mouse(cv2.EVENT_LBUTTONDOWN, 50, 415)
    assert app._back_requested is True


def test_clique_fora_do_voltar_chega_ao_modo():
    modo = FakeMode()
    app = App(AppConfig(), [modo])
    app.open_mode(0)
    app._back_rect = Rect(10, 400, 100, 30)
    app.on_mouse(cv2.EVENT_LBUTTONDOWN, 300, 100)
    assert app._back_requested is False
    assert modo.cliques == [(cv2.EVENT_LBUTTONDOWN, 300, 100)]


def test_voltar_nao_aparece_no_menu():
    app = App(AppConfig(), [FakeMode()])
    app._back_rect = Rect(10, 400, 100, 30)
    app.on_mouse(cv2.EVENT_LBUTTONDOWN, 50, 415)
    assert app._back_requested is False, "no menu não há para onde voltar"


def test_modo_recebe_o_frame_e_o_timestamp():
    """O contrato do `Mode`: recebe um frame BGR, devolve o frame anotado."""
    modo = FakeMode()
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    assert modo.process(frame, 42) is frame
    assert modo.processados == [42]
