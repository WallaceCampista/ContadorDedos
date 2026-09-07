"""Obtenção dos modelos do MediaPipe — baixados sob demanda, nunca versionados.

O download é genérico de propósito: a Fase 6 (identificação por face) precisa do
mesmo mecanismo para o modelo de rosto, mudando apenas a URL e o hash.
"""

from __future__ import annotations

import hashlib
import os
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


class ModelError(RuntimeError):
    """O modelo não está disponível e não pôde ser obtido."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(destination: Path, url: str, sha256: str) -> None:
    """Baixa um modelo para ``destination``, validando a integridade.

    Escreve primeiro em um arquivo temporário e só então renomeia, para que uma
    interrupção no meio do caminho nunca deixe um modelo truncado no lugar.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    print(f"Baixando {destination.name}…")
    try:
        with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while True:
                chunk = response.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if total:
                    print(f"\r  {downloaded * 100 // total:3d}%", end="", flush=True)
        print(f"\r  100%  ({downloaded / 1e6:.1f} MB)")
    except (urllib.error.URLError, OSError) as error:
        partial.unlink(missing_ok=True)
        raise ModelError(
            f"Não consegui baixar o modelo de {url}: {error}\n"
            f"Baixe manualmente e salve em {destination}."
        ) from error

    actual = _sha256(partial)
    if actual != sha256:
        partial.unlink(missing_ok=True)
        raise ModelError(
            f"O modelo baixado não confere com o hash esperado "
            f"(esperado {sha256}, obtido {actual}). "
            "O arquivo pode ter sido republicado na origem ou corrompido no caminho."
        )
    os.replace(partial, destination)


def ensure_model(path: Path, url: str, sha256: str, allow_download: bool = True) -> Path:
    """Garante que o modelo exista em ``path``, baixando-o se necessário."""
    if path.is_file():
        return path
    if not allow_download:
        raise ModelError(f"Modelo não encontrado em {path}.")
    download_model(path, url, sha256)
    return path


def ensure_model_from_archive(
    path: Path,
    url: str,
    archive_sha256: str,
    member: str,
    sha256: str,
    allow_download: bool = True,
) -> Path:
    """Extrai um modelo de dentro de um ``.zip`` publicado, e só guarda o modelo.

    O ArcFace é distribuído em um pacote com vários modelos, dos quais usamos um.
    Baixamos o pacote uma vez, tiramos o arquivo que interessa e descartamos o
    resto — ficam ~14 MB em disco, não os ~122 MB do pacote.
    """
    if path.is_file():
        return path
    if not allow_download:
        raise ModelError(f"Modelo não encontrado em {path}.")

    archive = path.with_suffix(".archive.zip")
    download_model(archive, url, archive_sha256)
    try:
        with zipfile.ZipFile(archive) as bundle:
            try:
                data = bundle.read(member)
            except KeyError as error:
                raise ModelError(f"O pacote baixado não contém {member}.") from error
    except zipfile.BadZipFile as error:
        raise ModelError(f"O pacote baixado em {archive} não é um zip válido.") from error
    finally:
        archive.unlink(missing_ok=True)

    actual = hashlib.sha256(data).hexdigest()
    if actual != sha256:
        raise ModelError(
            f"O modelo {member} não confere com o hash esperado "
            f"(esperado {sha256}, obtido {actual})."
        )
    partial = path.with_suffix(path.suffix + ".part")
    partial.write_bytes(data)
    os.replace(partial, path)
    return path
