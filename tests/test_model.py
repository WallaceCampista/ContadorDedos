"""Testes do download do modelo — sem rede: o `urlopen` é substituído."""

from __future__ import annotations

import hashlib
import urllib.error

import pytest

from contador_dedos.vision import model as model_module
from contador_dedos.vision.hands import HAND_MODEL_SHA256, HAND_MODEL_URL
from contador_dedos.vision.model import ModelError, download_model, ensure_model

PAYLOAD = b"modelo-de-mentira" * 1000
URL = "https://exemplo.invalido/modelo.task"
SHA_PAYLOAD = hashlib.sha256(PAYLOAD).hexdigest()


class FakeResponse:
    """Imita o objeto devolvido por ``urllib.request.urlopen``."""

    def __init__(self, data: bytes, com_tamanho: bool = True):
        self._data = data
        self._pos = 0
        self.headers = {"Content-Length": str(len(data))} if com_tamanho else {}

    def read(self, size: int) -> bytes:
        chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture
def servindo(monkeypatch):
    """Faz o download devolver os bytes pedidos, sem tocar na rede."""

    def _servir(data: bytes, com_tamanho: bool = True):
        monkeypatch.setattr(
            model_module.urllib.request,
            "urlopen",
            lambda *args, **kwargs: FakeResponse(data, com_tamanho),
        )

    return _servir


def test_baixa_e_grava_o_arquivo(tmp_path, servindo):
    servindo(PAYLOAD)
    destino = tmp_path / "sub" / "modelo.task"
    download_model(destino, URL, SHA_PAYLOAD)
    assert destino.read_bytes() == PAYLOAD


def test_cria_o_diretorio_de_destino(tmp_path, servindo):
    servindo(PAYLOAD)
    destino = tmp_path / "a" / "b" / "modelo.task"
    download_model(destino, URL, SHA_PAYLOAD)
    assert destino.is_file()


def test_funciona_sem_content_length(tmp_path, servindo):
    """Alguns servidores omitem o cabeçalho; a barra de progresso é opcional."""
    servindo(PAYLOAD, com_tamanho=False)
    destino = tmp_path / "modelo.task"
    download_model(destino, URL, SHA_PAYLOAD)
    assert destino.read_bytes() == PAYLOAD


def test_hash_divergente_e_recusado(tmp_path, monkeypatch):
    monkeypatch.setattr(
        model_module.urllib.request,
        "urlopen",
        lambda *args, **kwargs: FakeResponse(b"conteudo-corrompido"),
    )
    destino = tmp_path / "modelo.task"
    with pytest.raises(ModelError, match="hash esperado"):
        download_model(destino, URL, SHA_PAYLOAD)
    assert not destino.exists(), "um modelo inválido não pode ficar no lugar"
    assert list(tmp_path.iterdir()) == [], "sobrou arquivo temporário"


def test_falha_de_rede_nao_deixa_arquivo_parcial(tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise urllib.error.URLError("sem conexão")

    monkeypatch.setattr(model_module.urllib.request, "urlopen", explode)
    destino = tmp_path / "modelo.task"
    with pytest.raises(ModelError, match="Não consegui baixar"):
        download_model(destino, URL, SHA_PAYLOAD)
    assert list(tmp_path.iterdir()) == []


def test_ensure_model_devolve_arquivo_existente_sem_baixar(tmp_path, monkeypatch):
    def nao_deveria_baixar(*args, **kwargs):
        raise AssertionError("baixou um modelo que já estava em disco")

    monkeypatch.setattr(model_module, "download_model", nao_deveria_baixar)
    destino = tmp_path / "modelo.task"
    destino.write_bytes(b"ja-existo")
    assert ensure_model(destino, URL, SHA_PAYLOAD) == destino


def test_ensure_model_baixa_quando_falta(tmp_path, servindo):
    servindo(PAYLOAD)
    destino = tmp_path / "modelo.task"
    assert ensure_model(destino, URL, SHA_PAYLOAD) == destino
    assert destino.read_bytes() == PAYLOAD


def test_ensure_model_sem_download_avisa_o_caminho(tmp_path):
    destino = tmp_path / "modelo.task"
    with pytest.raises(ModelError, match=str(destino)):
        ensure_model(destino, URL, SHA_PAYLOAD, allow_download=False)


def test_constantes_do_modelo_de_maos_sao_coerentes():
    """A URL é versionada, então o hash fixado precisa acompanhá-la."""
    assert HAND_MODEL_URL.endswith("hand_landmarker.task")
    assert "/1/" in HAND_MODEL_URL, "a URL precisa apontar para uma versão fixa"
    assert len(HAND_MODEL_SHA256) == 64
