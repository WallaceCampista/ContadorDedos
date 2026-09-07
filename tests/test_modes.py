"""Testes do contrato `Mode`, do registro e do roteamento do `App`."""

from __future__ import annotations

import numpy as np
import pytest

from contador_dedos.app import App, should_quit
from contador_dedos.config import AppConfig
from contador_dedos.modes import MODE_FACTORIES, Mode, build_modes, close_modes
from contador_dedos.modes.finger_counter import FingerCounter


class FakeMode(Mode):
    """Modo mínimo: registra o que recebeu, sem tocar em câmera ou modelo."""

    name = "Falso"
    icon = "🧪"
    hint = "dica"

    def __init__(self, falha_ao_fechar: bool = False):
        self.processados = []
        self.fechado = False
        self._falha_ao_fechar = falha_ao_fechar

    def process(self, frame, timestamp_ms: int = 0):
        self.processados.append(timestamp_ms)
        return frame

    def close(self) -> None:
        self.fechado = True
        if self._falha_ao_fechar:
            raise RuntimeError("boom")


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


def test_finger_counter_se_apresenta_para_o_menu():
    """O menu da Fase 4 monta os cards a partir destes atributos."""
    assert FingerCounter.name
    assert FingerCounter.icon
    assert issubclass(FingerCounter, Mode)


def test_registro_nao_esta_vazio():
    assert MODE_FACTORIES


def test_build_modes_repassa_a_config(monkeypatch):
    recebidos = []

    def fabrica(config):
        recebidos.append(config)
        return FakeMode()

    monkeypatch.setattr("contador_dedos.modes.MODE_FACTORIES", (fabrica, fabrica))
    config = AppConfig(camera_index=3)
    modos = build_modes(config)
    assert len(modos) == 2
    assert recebidos == [config, config]


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


def test_app_entra_no_primeiro_modo():
    """Sem menu ainda, o app abre direto no primeiro modo registrado."""
    primeiro, segundo = FakeMode(), FakeMode()
    app = App(AppConfig(), [primeiro, segundo])
    assert app.screen is primeiro
    assert app.running is True


@pytest.mark.parametrize("tecla", [ord("q"), ord("Q"), 27])
def test_teclas_de_saida_param_o_loop(tecla):
    app = App(AppConfig(), [FakeMode()])
    app.handle_key(tecla)
    assert app.running is False


@pytest.mark.parametrize("tecla", [ord("a"), 255, ord(" ")])
def test_outras_teclas_nao_param_o_loop(tecla):
    app = App(AppConfig(), [FakeMode()])
    app.handle_key(tecla)
    assert app.running is True
    assert should_quit(tecla) is False


def test_modo_recebe_o_frame_e_o_timestamp():
    """O contrato do `Mode`: recebe um frame BGR, devolve o frame anotado."""
    modo = FakeMode()
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    assert modo.process(frame, 42) is frame
    assert modo.processados == [42]
