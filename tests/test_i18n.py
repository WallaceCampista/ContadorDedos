"""Testes da tradução — inclusive a varredura que cobra strings novas."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import contador_dedos
from contador_dedos.i18n import (
    CATALOG,
    DEFAULT_LANGUAGE,
    LANGUAGES,
    get_language,
    set_language,
    t,
)

FONTE = Path(contador_dedos.__file__).parent
#: Casa `t("…")` e `t('…')`, inclusive quebrados em várias linhas pelo Black.
CHAMADAS = re.compile(r"""\bt\(\s*(["'])(.+?)\1\s*\)""", re.DOTALL)


@pytest.fixture(autouse=True)
def idioma_limpo():
    """Cada teste começa e termina em português."""
    set_language(DEFAULT_LANGUAGE)
    yield
    set_language(DEFAULT_LANGUAGE)


def strings_traduzidas_no_codigo() -> set[str]:
    encontradas = set()
    for arquivo in FONTE.rglob("*.py"):
        if arquivo.name == "i18n.py":
            continue
        for _, texto in CHAMADAS.findall(arquivo.read_text()):
            encontradas.add(texto)
    return encontradas


def test_a_varredura_acha_chamadas_de_verdade():
    """Se o regex parar de casar, o teste seguinte viraria um falso positivo."""
    achadas = strings_traduzidas_no_codigo()
    assert len(achadas) > 20
    assert "Esquerda" in achadas


def test_toda_string_marcada_tem_traducao():
    """A rede que impede um rótulo novo de ficar só em português."""
    literais = {s for s in strings_traduzidas_no_codigo() if not s.startswith(("{", "self"))}
    faltando = sorted(literais - set(CATALOG))
    assert not faltando, f"sem tradução no CATALOG: {faltando}"


def test_marcadores_sao_preservados_na_traducao():
    """Trocar `{n}` por outro nome quebraria o `.format()` em tempo de execução."""
    marcador = re.compile(r"\{(\w+)\}")
    for origem, destino in CATALOG.items():
        assert set(marcador.findall(origem)) == set(marcador.findall(destino)), origem


def test_portugues_devolve_o_proprio_texto():
    assert t("Esquerda") == "Esquerda"
    assert get_language() == "pt"


def test_ingles_traduz():
    set_language("en")
    assert t("Esquerda") == "Left"
    assert t("Nenhuma mão detectada") == "No hand detected"


def test_string_sem_traducao_cai_no_portugues():
    """Degradar para o original é melhor que estourar na cara do usuário."""
    set_language("en")
    assert t("um rótulo que ninguém traduziu") == "um rótulo que ninguém traduziu"


def test_idioma_invalido_e_recusado():
    with pytest.raises(ValueError, match="não suportado"):
        set_language("tlh")
    assert get_language() == DEFAULT_LANGUAGE, "o idioma não pode mudar em caso de erro"


@pytest.mark.parametrize("idioma", LANGUAGES)
def test_todos_os_idiomas_declarados_funcionam(idioma):
    set_language(idioma)
    assert isinstance(t("Total"), str)


def test_catalogo_nao_tem_traducao_vazia():
    vazias = [chave for chave, valor in CATALOG.items() if not valor.strip()]
    assert not vazias


def test_nomes_dos_modos_estao_traduzidos():
    """Os cards do menu saem do `name` de cada modo."""
    from contador_dedos.modes import MODE_FACTORIES

    assert len(MODE_FACTORIES) == 4
    for nome in ("Contar Dedos", "Gestos", "Libras", "Rosto (ID)"):
        assert nome in CATALOG


def test_o_texto_de_consentimento_esta_todo_traduzido():
    """A tela de LGPD em inglês não pode sair pela metade."""
    from contador_dedos.modes.face_id import CONSENT_LINES, CONSENT_TITLE

    set_language("en")
    assert t(CONSENT_TITLE) != CONSENT_TITLE
    for linha in CONSENT_LINES:
        if linha:
            assert t(linha) != linha, f"linha do consentimento sem tradução: {linha}"
