"""Sobe a página Streamlit — o que o comando `contador-dedos-web` executa."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

PAGE = Path(__file__).with_name("page.py")
#: Só o laço local. A base de rostos é dado biométrico: expor a página na rede
#: mudaria completamente o perfil de risco, e não é o que este projeto promete.
DEFAULT_ADDRESS = "127.0.0.1"
DEFAULT_PORT = "8501"

MISSING_DEPS = (
    "As dependências web não estão instaladas.\n"
    'Instale com:  pip install -e ".[web]"   (ou ./setup.sh --web)'
)


def build_command(argv: Sequence[str] | None = None) -> list[str]:
    """Monta a linha do Streamlit. Argumentos extras são repassados a ele."""
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(PAGE),
        "--server.address",
        DEFAULT_ADDRESS,
        "--server.port",
        DEFAULT_PORT,
        "--browser.gatherUsageStats",
        "false",
        *(argv or []),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Devolve 0 em caso de sucesso, 1 quando falta dependência."""
    try:
        import streamlit  # noqa: F401
        import streamlit_webrtc  # noqa: F401
    except ImportError:
        print(MISSING_DEPS, file=sys.stderr)
        return 1

    print(f"Abrindo em http://{DEFAULT_ADDRESS}:{DEFAULT_PORT}  (Ctrl+C encerra)")
    try:
        return subprocess.call(build_command(argv if argv is not None else sys.argv[1:]))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
