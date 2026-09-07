"""Testes do feedback sonoro — sem tocar nada de verdade."""

from __future__ import annotations

import numpy as np
import pytest

from contador_dedos.core import audio
from contador_dedos.core.audio import AMPLITUDE, SAMPLE_RATE, TONES, Beeper, tone_wave


class FakeSoundDevice:
    """Registra o que seria tocado."""

    def __init__(self, falha: Exception | None = None):
        self.tocados = []
        self.parou = False
        self._falha = falha

    def play(self, data, samplerate, blocking=False):
        if self._falha:
            raise self._falha
        self.tocados.append((len(data), samplerate))

    def stop(self):
        self.parou = True


def com_backend(beeper: Beeper, backend) -> Beeper:
    beeper._sounddevice = backend
    return beeper


def test_onda_tem_a_duracao_pedida():
    onda = tone_wave(440.0, 0.1, sample_rate=1000)
    assert onda.shape == (100,)


def test_onda_respeita_o_volume():
    assert float(np.abs(tone_wave(440.0, 0.05)).max()) == pytest.approx(AMPLITUDE, abs=1e-3)


def test_onda_comeca_e_termina_no_silencio():
    """Sem o fade nas pontas, cada bipe sairia com um estalo."""
    onda = tone_wave(880.0, 0.06)
    assert abs(float(onda[0])) < 1e-3
    assert abs(float(onda[-1])) < 1e-3


def test_duracao_minima_nao_gera_onda_vazia():
    assert tone_wave(440.0, 0.0).shape == (1,)


@pytest.mark.parametrize("tom", sorted(TONES))
def test_toca_os_tons_conhecidos(tom):
    backend = FakeSoundDevice()
    beeper = com_backend(Beeper(enabled=True), backend)
    assert beeper.play(tom) is True
    assert backend.tocados[0][1] == SAMPLE_RATE


def test_desabilitado_nao_toca():
    backend = FakeSoundDevice()
    assert com_backend(Beeper(enabled=False), backend).play("change") is False
    assert backend.tocados == []


def test_tom_desconhecido_e_ignorado():
    backend = FakeSoundDevice()
    assert com_backend(Beeper(enabled=True), backend).play("inexistente") is False


def test_falha_de_audio_desliga_o_som_sem_derrubar_o_app():
    """Sem PortAudio ou sem placa: o app segue, mudo."""
    backend = FakeSoundDevice(falha=OSError("sem PortAudio"))
    beeper = com_backend(Beeper(enabled=True), backend)
    assert beeper.play("change") is False
    assert beeper.enabled is False
    assert "PortAudio" in beeper.error
    assert beeper.play("change") is False, "não insiste depois de falhar"


def test_close_para_o_backend():
    backend = FakeSoundDevice()
    beeper = com_backend(Beeper(enabled=True), backend)
    beeper.close()
    assert backend.parou is True


def test_close_sem_backend_e_inofensivo():
    Beeper(enabled=True).close()


def test_close_engole_falha_do_backend():
    backend = FakeSoundDevice()
    backend.stop = lambda: (_ for _ in ()).throw(OSError("já fechado"))
    com_backend(Beeper(enabled=True), backend).close()


def test_instancia_padrao_comeca_desligada():
    assert audio.configure(False).enabled is False
    assert audio.beep("change") is False


def test_configure_liga_e_desliga():
    beeper = audio.configure(True)
    assert beeper.enabled is True
    audio.configure(False)
    assert beeper.enabled is False
