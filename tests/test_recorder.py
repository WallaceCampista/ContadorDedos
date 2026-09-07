"""Testes de snapshots e gravação de vídeo."""

from __future__ import annotations

from datetime import datetime

import cv2
import numpy as np
import pytest

from contador_dedos.core.recorder import (
    PREFIX,
    Recorder,
    RecorderError,
    timestamped_name,
)


def frame(width: int = 64, height: int = 48, tom: int = 120) -> np.ndarray:
    return np.full((height, width, 3), tom, dtype=np.uint8)


@pytest.fixture
def recorder(tmp_path) -> Recorder:
    return Recorder(tmp_path / "capturas", fps=10.0)


def test_nome_leva_data_e_hora():
    nome = timestamped_name("png", datetime(2026, 9, 7, 15, 4, 5))
    assert nome == f"{PREFIX}_20260907-150405.png"


def test_nomes_diferentes_nao_colidem():
    a = timestamped_name("mp4", datetime(2026, 9, 7, 15, 4, 5))
    b = timestamped_name("mp4", datetime(2026, 9, 7, 15, 4, 6))
    assert a != b


def test_snapshot_grava_o_arquivo(recorder):
    caminho = recorder.snapshot(frame())
    assert caminho.is_file()
    assert caminho.suffix == ".png"
    assert cv2.imread(str(caminho)).shape == (48, 64, 3)


def test_snapshot_cria_a_pasta_de_saida(recorder):
    assert not recorder.output_dir.exists()
    recorder.snapshot(frame())
    assert recorder.output_dir.is_dir()


def test_snapshot_preserva_o_conteudo(recorder):
    img = frame(tom=200)
    lido = cv2.imread(str(recorder.snapshot(img)))
    assert np.array_equal(lido, img), "o PNG é sem perdas"


def test_comeca_sem_gravar(recorder):
    assert recorder.is_recording is False
    assert recorder.elapsed == 0.0


def test_write_sem_gravacao_e_inofensivo(recorder):
    recorder.write(frame())  # não pode estourar
    assert recorder.is_recording is False


def test_ciclo_de_gravacao(recorder):
    destino = recorder.start(frame())
    assert recorder.is_recording is True
    assert destino.suffix == ".mp4"
    for _ in range(5):
        recorder.write(frame())
    assert recorder.elapsed >= 0.0
    assert recorder.stop() == destino
    assert recorder.is_recording is False
    assert destino.is_file() and destino.stat().st_size > 0


def test_toggle_alterna(recorder):
    iniciado = recorder.toggle(frame())
    assert recorder.is_recording is True
    recorder.write(frame())
    assert recorder.toggle(frame()) == iniciado
    assert recorder.is_recording is False


def test_start_duplicado_nao_abre_outro_arquivo(recorder):
    primeiro = recorder.start(frame())
    assert recorder.start(frame()) == primeiro


def test_stop_sem_gravacao_devolve_none(recorder):
    assert recorder.stop() is None


def test_close_encerra_gravacao_pendente(recorder):
    destino = recorder.start(frame())
    recorder.write(frame())
    recorder.close()
    assert recorder.is_recording is False
    assert destino.is_file()


def test_video_sai_no_tamanho_do_frame(recorder):
    recorder.start(frame(width=96, height=64))
    for _ in range(6):
        recorder.write(frame(width=96, height=64))
    destino = recorder.stop()
    captura = cv2.VideoCapture(str(destino))
    try:
        assert captura.isOpened()
        assert int(captura.get(cv2.CAP_PROP_FRAME_WIDTH)) == 96
        assert int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT)) == 64
    finally:
        captura.release()


def test_pasta_impossivel_de_criar_vira_erro_tratavel(tmp_path):
    """Um caminho inválido não pode derrubar o app no meio do loop."""
    arquivo = tmp_path / "arquivo"
    arquivo.write_text("nao sou pasta")
    recorder = Recorder(arquivo / "dentro")
    with pytest.raises((RecorderError, OSError)):
        recorder.snapshot(frame())
