"""Testes da base local de rostos — inclusive as garantias de LGPD."""

from __future__ import annotations

import json
import os
import stat

import numpy as np
import pytest

from contador_dedos.storage.faces_db import (
    MAX_NAME_LENGTH,
    SCHEMA_VERSION,
    FaceDB,
    FaceDBError,
)

DIM = 8


def vetor(indice: int, dim: int = DIM) -> np.ndarray:
    """Vetor unitário no eixo `indice` — distância de cosseno 1 entre eixos."""
    v = np.zeros(dim, dtype=np.float32)
    v[indice] = 1.0
    return v


@pytest.fixture
def db(tmp_path) -> FaceDB:
    return FaceDB(tmp_path / "faces.npz", dimension=DIM)


def test_base_nova_comeca_vazia(db):
    assert len(db) == 0
    assert db.names() == []
    assert not db.path.exists()


def test_cadastra_e_encontra(db):
    db.add("Ana", vetor(0))
    nome, distancia = db.match(vetor(0), threshold=0.6)
    assert nome == "Ana"
    assert distancia == pytest.approx(0.0, abs=1e-6)


def test_rosto_distante_vira_desconhecido(db):
    db.add("Ana", vetor(0))
    nome, distancia = db.match(vetor(1), threshold=0.6)
    assert nome is None, "além do limiar, tem que ser Desconhecido"
    assert distancia == pytest.approx(1.0)


def test_limiar_maior_aceita_mais_longe(db):
    db.add("Ana", vetor(0))
    assert db.match(vetor(1), threshold=0.5)[0] is None
    assert db.match(vetor(1), threshold=1.0)[0] == "Ana"


def test_escolhe_o_mais_proximo_entre_varios(db):
    db.add("Ana", vetor(0))
    db.add("Bruno", vetor(1))
    quase_bruno = np.array([0.2, 0.98, 0, 0, 0, 0, 0, 0], dtype=np.float32)
    assert db.match(quase_bruno, threshold=0.6)[0] == "Bruno"


def test_base_vazia_nao_reconhece_ninguem(db):
    nome, distancia = db.match(vetor(0), threshold=1.0)
    assert nome is None
    assert distancia == float("inf")


def test_recadastrar_substitui_sem_duplicar(db):
    db.add("Ana", vetor(0))
    db.add("Ana", vetor(1))
    assert db.names() == ["Ana"]
    assert db.match(vetor(1), threshold=0.1)[0] == "Ana"


def test_embedding_e_normalizado_ao_entrar(db):
    db.add("Ana", vetor(0) * 42.0)
    assert db.match(vetor(0), threshold=0.01)[0] == "Ana"


def test_nome_vazio_e_recusado(db):
    with pytest.raises(ValueError, match="vazio"):
        db.add("   ", vetor(0))


def test_nome_longo_demais_e_recusado(db):
    with pytest.raises(ValueError, match="caracteres"):
        db.add("a" * (MAX_NAME_LENGTH + 1), vetor(0))


def test_dimensao_incompativel_e_recusada(db):
    db.add("Ana", vetor(0))
    with pytest.raises(ValueError, match="dimensões"):
        db.add("Bruno", np.ones(DIM + 1, dtype=np.float32))


# --- direito ao esquecimento ------------------------------------------------


def test_exclusao_remove_o_cadastro(db):
    db.add("Ana", vetor(0))
    db.add("Bruno", vetor(1))
    assert db.delete("Ana") is True
    assert db.names() == ["Bruno"]
    assert db.match(vetor(0), threshold=0.6)[0] is None


def test_exclusao_de_quem_nao_existe_e_inofensiva(db):
    assert db.delete("Ninguém") is False


def test_exclusao_persiste_em_disco(db):
    db.add("Ana", vetor(0))
    db.add("Bruno", vetor(1))
    db.delete("Ana")
    assert FaceDB(db.path).names() == ["Bruno"]


def test_clear_apaga_os_arquivos(db):
    db.add("Ana", vetor(0))
    assert db.path.exists() and db.index_path.exists()
    db.clear()
    assert not db.path.exists()
    assert not db.index_path.exists()
    assert len(db) == 0


# --- persistência e privacidade ---------------------------------------------


def test_base_sobrevive_ao_reinicio(db):
    db.add("Ana", vetor(0))
    db.add("Bruno", vetor(1))
    recarregada = FaceDB(db.path)
    assert recarregada.names() == ["Ana", "Bruno"]
    assert recarregada.match(vetor(1), threshold=0.1)[0] == "Bruno"


def test_arquivos_sao_privados_do_usuario(db):
    """Dado biométrico não pode ficar legível para outros usuários da máquina."""
    db.add("Ana", vetor(0))
    for caminho in (db.path, db.index_path):
        modo = stat.S_IMODE(os.stat(caminho).st_mode)
        assert modo == 0o600, f"{caminho.name} está com permissão {oct(modo)}"


def test_indice_json_lista_nomes_sem_expor_vetores(db):
    db.add("Ana", vetor(0))
    dados = json.loads(db.index_path.read_text())
    assert dados["schema"] == SCHEMA_VERSION
    assert dados["names"] == ["Ana"]
    assert "embedding" not in json.dumps(dados).lower().replace("embeddings;", "")
    assert "updated_at" in dados


def test_nao_sobra_arquivo_temporario(db):
    db.add("Ana", vetor(0))
    assert not list(db.path.parent.glob("*.part"))


def test_base_corrompida_avisa_em_vez_de_estourar(tmp_path):
    caminho = tmp_path / "faces.npz"
    caminho.write_bytes(b"isso nao e um npz")
    with pytest.raises(FaceDBError, match="Não consegui ler"):
        FaceDB(caminho)


def test_base_inconsistente_e_recusada(tmp_path):
    """Nomes e vetores em quantidades diferentes: melhor falhar alto."""
    caminho = tmp_path / "faces.npz"
    with caminho.open("wb") as handle:
        np.savez(
            handle,
            names=np.array(["Ana", "Bruno"], dtype="U64"),
            embeddings=np.zeros((1, DIM), dtype=np.float32),
        )
    with pytest.raises(FaceDBError, match="inconsistente"):
        FaceDB(caminho)
