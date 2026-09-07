"""Testes do anti-flicker e do medidor de FPS."""

from __future__ import annotations

import pytest

from contador_dedos import CountSmoother, FpsMeter


def test_janela_precisa_ser_positiva():
    with pytest.raises(ValueError, match="janela"):
        CountSmoother(0)


def test_primeira_leitura_aparece_imediatamente():
    assert CountSmoother(5).update(3) == 3


def test_leitura_isolada_nao_derruba_o_valor_estavel():
    """O caso que motivou o componente: um frame ruim no meio de vários bons."""
    smoother = CountSmoother(5)
    for _ in range(4):
        smoother.update(5)
    assert smoother.update(2) == 5


def test_valor_novo_assume_quando_vira_maioria():
    smoother = CountSmoother(3)
    for _ in range(3):
        smoother.update(5)
    assert smoother.update(2) == 5  # 5,5,2
    assert smoother.update(2) == 2  # 5,2,2


def test_mao_ausente_some_apos_encher_a_janela():
    smoother = CountSmoother(3)
    for _ in range(3):
        smoother.update(4)
    assert smoother.update(None) == 4
    assert smoother.update(None) is None


def test_janela_unitaria_nao_suaviza():
    smoother = CountSmoother(1)
    assert [smoother.update(v) for v in (1, 4, 2)] == [1, 4, 2]


def test_fps_comeca_zerado():
    assert FpsMeter().tick(0.0) == 0.0


def test_fps_usa_o_intervalo_entre_ticks():
    meter = FpsMeter(smoothing=0.0)  # sem memória: mede o instante
    meter.tick(0.0)
    assert meter.tick(0.02) == pytest.approx(50.0)
    assert meter.tick(0.04) == pytest.approx(50.0)


def test_fps_suaviza_variacoes():
    """Com suavização alta, um frame lento isolado quase não move o número."""
    meter = FpsMeter(smoothing=0.9)
    meter.tick(0.0)
    estavel = meter.tick(0.01)  # 100 FPS
    depois = meter.tick(0.11)  # um frame de 10 FPS
    assert depois < estavel
    assert depois > 50  # mas longe de despencar para 10


def test_fps_ignora_ticks_sem_tempo_decorrido():
    meter = FpsMeter(smoothing=0.0)
    meter.tick(1.0)
    meter.tick(1.5)
    assert meter.tick(1.5) == pytest.approx(2.0)  # inalterado, sem divisão por zero
