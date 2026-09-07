"""Testes do anti-flicker, do medidor de FPS e do relógio do vídeo."""

from __future__ import annotations

import pytest

from contador_dedos.core.pipeline import FpsMeter, ValueSmoother, VideoClock


def test_janela_precisa_ser_positiva():
    with pytest.raises(ValueError, match="janela"):
        ValueSmoother(0)


def test_primeira_leitura_aparece_imediatamente():
    assert ValueSmoother(5).update(3) == 3


def test_leitura_isolada_nao_derruba_o_valor_estavel():
    """O caso que motivou o componente: um frame ruim no meio de vários bons."""
    smoother = ValueSmoother(5)
    for _ in range(4):
        smoother.update(5)
    assert smoother.update(2) == 5


def test_valor_novo_assume_quando_vira_maioria():
    smoother = ValueSmoother(3)
    for _ in range(3):
        smoother.update(5)
    assert smoother.update(2) == 5  # 5,5,2
    assert smoother.update(2) == 2  # 5,2,2


def test_mao_ausente_some_apos_encher_a_janela():
    smoother = ValueSmoother(3)
    for _ in range(3):
        smoother.update(4)
    assert smoother.update(None) == 4
    assert smoother.update(None) is None


def test_janela_unitaria_nao_suaviza():
    smoother = ValueSmoother(1)
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


def test_relogio_comeca_no_zero():
    assert VideoClock(started=0.0).tick(0.0) == 0


def test_relogio_converte_segundos_em_milissegundos():
    clock = VideoClock(started=0.0)
    assert clock.tick(0.5) == 500
    assert clock.tick(1.25) == 1250


def test_relogio_nunca_repete_o_mesmo_timestamp():
    """O modo de vídeo do MediaPipe rejeita timestamps que não avançam."""
    clock = VideoClock(started=0.0)
    # Vários quadros dentro do mesmo milissegundo: um loop rápido faz isso.
    marcas = [clock.tick(0.0) for _ in range(5)]
    assert marcas == [0, 1, 2, 3, 4]


def test_relogio_avanca_mesmo_se_o_tempo_andar_para_tras():
    clock = VideoClock(started=0.0)
    primeiro = clock.tick(1.0)
    assert clock.tick(0.5) > primeiro


def test_relogio_usa_o_relogio_real_por_padrao():
    assert VideoClock().tick() >= 0


def test_suavizador_serve_para_qualquer_valor():
    """Contagens são inteiros; gestos são textos. O componente é o mesmo."""
    smoother = ValueSmoother(3)
    assert [smoother.update(v) for v in ("Paz", "Paz", "OK")] == ["Paz", "Paz", "Paz"]
    assert smoother.update("OK") == "OK"
