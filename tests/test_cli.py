"""Testes do parsing e da validação dos argumentos de linha de comando."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from contador_dedos.app import KEY_BACK, is_printable, should_quit
from contador_dedos.config import DEFAULT_MODEL_PATH, AppConfig, parse_args


def test_sem_argumentos_usa_os_padroes():
    assert parse_args([]) == AppConfig()


def test_argumentos_sao_refletidos_na_config():
    config = parse_args(
        [
            "--camera",
            "2",
            "--max-hands",
            "1",
            "--detection-confidence",
            "0.7",
            "--tracking-confidence",
            "0.8",
            "--smooth-window",
            "9",
            "--no-mirror",
            "--model",
            "/tmp/modelo.task",
        ]
    )
    assert config == AppConfig(
        camera_index=2,
        max_hands=1,
        detection_confidence=0.7,
        tracking_confidence=0.8,
        mirror=False,
        smooth_window=9,
        model_path=Path("/tmp/modelo.task"),
    )


def test_modelo_tem_caminho_padrao():
    assert parse_args([]).model_path == DEFAULT_MODEL_PATH
    assert DEFAULT_MODEL_PATH.name == "hand_landmarker.task"


@pytest.mark.parametrize("flag", [["--mirror"], ["--no-mirror"], []])
def test_espelhamento(flag):
    esperado = flag != ["--no-mirror"]
    assert parse_args(flag).mirror is esperado


@pytest.mark.parametrize(
    "argumentos",
    [
        ["--camera", "-1"],
        ["--max-hands", "0"],
        ["--max-hands", "-3"],
        ["--smooth-window", "0"],
        ["--detection-confidence", "1.5"],
        ["--detection-confidence", "-0.1"],
        ["--tracking-confidence", "2"],
        ["--mirror", "--no-mirror"],  # mutuamente exclusivos
        ["--camera", "abc"],
    ],
)
def test_argumentos_invalidos_encerram_com_erro(argumentos):
    with pytest.raises(SystemExit) as excinfo:
        parse_args(argumentos)
    assert excinfo.value.code == 2


@pytest.mark.parametrize("valor", ["0", "1", "0.5"])
def test_limites_das_confiancas_sao_aceitos(valor):
    assert parse_args(["--detection-confidence", valor]).detection_confidence == float(valor)


def test_config_e_imutavel():
    """A config é injetada e não deve ser alterada em tempo de execução."""
    with pytest.raises(FrozenInstanceError):
        parse_args([]).camera_index = 3


@pytest.mark.parametrize(("tecla", "encerra"), [("q", True), ("Q", True), ("a", False)])
def test_should_quit_por_letra(tecla, encerra):
    assert should_quit(ord(tecla)) is encerra


def test_esc_nao_encerra_mais():
    """Desde a Fase 4, o ESC volta ao menu — quem encerra é o Q."""
    assert should_quit(KEY_BACK) is False


def test_tecla_ausente_nao_encerra():
    assert should_quit(255) is False  # waitKey sem tecla pressionada


@pytest.mark.parametrize(
    ("codigo", "imprimivel"),
    [(ord("1"), True), (ord("z"), True), (255, False), (27, False), (10, False)],
)
def test_is_printable_filtra_o_que_nao_e_caractere(codigo, imprimivel):
    assert is_printable(codigo) is imprimivel
