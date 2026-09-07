"""Testes do front web.

O `launcher` é testável sempre (só usa a biblioteca padrão). O `engine` precisa
dos modelos, e a página precisa do Streamlit instalado — os dois são pulados
quando o que falta não está presente, para a CI não baixar nada.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from contador_dedos.config import DEFAULT_MODEL_PATH, AppConfig
from contador_dedos.vision.embedder import ARCFACE_FILENAME
from contador_dedos.vision.faces import FACE_MODEL_FILENAME
from contador_dedos.web.launcher import (
    DEFAULT_ADDRESS,
    DEFAULT_PORT,
    PAGE,
    build_command,
    main,
)

MODELS = DEFAULT_MODEL_PATH.parent
tem_modelo_de_maos = DEFAULT_MODEL_PATH.is_file()
tem_modelos_de_rosto = (MODELS / FACE_MODEL_FILENAME).is_file() and (
    MODELS / ARCFACE_FILENAME
).is_file()

try:  # o front web é um extra opcional
    import streamlit  # noqa: F401

    tem_streamlit = True
except ImportError:
    tem_streamlit = False


# --- launcher ---------------------------------------------------------------


def test_comando_roda_o_streamlit_na_pagina():
    comando = build_command([])
    assert comando[0] == sys.executable
    assert comando[1:4] == ["-m", "streamlit", "run"]
    assert comando[4] == str(PAGE)


def test_pagina_existe():
    assert PAGE.is_file()
    assert PAGE.name == "page.py"


def test_servidor_fica_apenas_no_laco_local():
    """A base de rostos é dado biométrico: expor a página na rede mudaria o
    perfil de risco, e não é o que o projeto promete."""
    assert DEFAULT_ADDRESS == "127.0.0.1"
    comando = build_command([])
    assert comando[comando.index("--server.address") + 1] == "127.0.0.1"


def test_telemetria_do_streamlit_desligada():
    comando = build_command([])
    assert comando[comando.index("--browser.gatherUsageStats") + 1] == "false"


def test_porta_padrao_declarada():
    comando = build_command([])
    assert comando[comando.index("--server.port") + 1] == DEFAULT_PORT


def test_argumentos_extras_sao_repassados():
    assert "--server.port" in build_command(["--server.port", "9000"])
    assert build_command(["--foo"])[-1] == "--foo"


def test_falta_de_dependencia_avisa_em_vez_de_estourar(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "streamlit", None)
    monkeypatch.setattr(
        "builtins.__import__",
        lambda name, *a, **k: (
            (_ for _ in ()).throw(ImportError(name))
            if name.startswith("streamlit")
            else __import__(name, *a, **k)
        ),
    )
    assert main([]) == 1
    assert "pip install" in capsys.readouterr().err


# --- engine (precisa dos modelos) -------------------------------------------


@pytest.fixture(scope="module")
def hand_engine():
    from contador_dedos.web.engine import HandEngine

    return HandEngine(AppConfig())


def frame(width: int = 320, height: int = 240) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


@pytest.mark.skipif(not tem_modelo_de_maos, reason="modelo de mãos ausente")
def test_o_front_web_reusa_os_modos_do_app(hand_engine):
    """A promessa da arquitetura: a moldura muda, a lógica é a mesma."""
    assert hand_engine.mode_names() == ["Contar Dedos", "Gestos", "Libras"]


@pytest.mark.skipif(not tem_modelo_de_maos, reason="modelo de mãos ausente")
def test_modo_de_rosto_fica_fora_do_engine_de_maos(hand_engine):
    """Ele tem detector e modelo próprios, carregados só quando escolhido."""
    assert "Rosto (ID)" not in hand_engine.mode_names()


@pytest.mark.skipif(not tem_modelo_de_maos, reason="modelo de mãos ausente")
@pytest.mark.parametrize("modo", ["Contar Dedos", "Gestos", "Libras"])
def test_cada_modo_anota_o_frame(hand_engine, modo):
    original = frame()
    anotado = hand_engine.process(original.copy(), modo, mirrored=True)
    assert anotado.shape == original.shape
    assert (anotado != original).any(), "o modo não desenhou nada"


@pytest.mark.skipif(not tem_modelo_de_maos, reason="modelo de mãos ausente")
def test_modo_desconhecido_devolve_o_frame_intacto(hand_engine):
    original = frame()
    assert np.array_equal(hand_engine.process(original.copy(), "Inexistente", True), original)


@pytest.mark.skipif(not tem_modelo_de_maos, reason="modelo de mãos ausente")
def test_timestamps_avancam_entre_frames(hand_engine):
    """O modo de vídeo do MediaPipe rejeita timestamps que não crescem."""
    primeiro = hand_engine.clock.tick()
    hand_engine.process(frame(), "Contar Dedos", True)
    assert hand_engine.clock.tick() > primeiro


def test_espelhamento():
    from contador_dedos.web.engine import mirror

    marcado = np.zeros((4, 4, 3), dtype=np.uint8)
    marcado[:, 0] = 9
    assert mirror(marcado, True)[0, -1, 0] == 9
    assert mirror(marcado, False)[0, 0, 0] == 9


@pytest.mark.skipif(not tem_modelos_de_rosto, reason="modelos de rosto ausentes")
def test_engine_de_rosto_anota_sem_quebrar(tmp_path):
    from contador_dedos.web.engine import FaceEngine

    engine = FaceEngine(AppConfig(faces_db=tmp_path / "faces.npz"))
    saida = engine.process(frame(), engine.db(), 0.62, mirrored=True)
    assert saida.shape == (240, 320, 3)


# --- página (precisa do Streamlit) ------------------------------------------


@pytest.mark.skipif(not tem_streamlit, reason="extra [web] não instalado")
def test_a_pagina_renderiza_os_controles():
    """Roda o script de verdade. Pegou dois bugs que o HTTP 200 escondia:
    import relativo em script solto e argumento de RTC obsoleto."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(PAGE), default_timeout=300)
    at.run()

    rotulos = {r.label: list(r.options) for r in at.sidebar.radio}
    assert "Idioma / Language" in rotulos
    modos = next(op for rot, op in rotulos.items() if "Rosto (ID)" in op)
    assert modos == ["Contar Dedos", "Gestos", "Libras", "Rosto (ID)"]
    assert at.sidebar.toggle[0].value is True, "espelho ligado por padrão"

    # O `webrtc_streamer` exige uma sessão real do runtime, que o AppTest não
    # tem — é a única exceção tolerada aqui.
    for excecao in at.exception:
        assert "_session_mgr" in excecao.value, excecao.value


@pytest.mark.skipif(not tem_streamlit, reason="extra [web] não instalado")
def test_a_pagina_usa_imports_absolutos():
    """O Streamlit executa a página fora do pacote: relativo quebraria."""
    codigo = Path(PAGE).read_text()
    assert "from contador_dedos." in codigo
    assert "\nfrom .." not in codigo and "\nfrom ." not in codigo
