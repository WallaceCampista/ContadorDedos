"""Base local de rostos cadastrados.

Guarda **embeddings** — vetores de identidade —, nunca as fotos originais. Isso
é minimização de dados: o vetor serve para comparar, mas não reconstrói a
imagem do rosto.

Dado biométrico facial é **dado pessoal sensível** (LGPD, Art. 5º, II). Por isso
esta camada: (a) grava apenas em disco local, sem nenhuma chamada de rede;
(b) restringe a permissão do arquivo ao próprio usuário; e (c) implementa
:meth:`FaceDB.delete`, o direito ao esquecimento.
"""

from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..vision.embedder import cosine_distance, normalize

#: Formato do arquivo. Muda se a estrutura mudar de forma incompatível.
SCHEMA_VERSION = 1
#: Só o dono lê e escreve — é dado sensível.
FILE_MODE = stat.S_IRUSR | stat.S_IWUSR
#: Limite do nome cadastrado — também é o que cabe no formato do arquivo.
MAX_NAME_LENGTH = 64


class FaceDBError(RuntimeError):
    """A base de rostos não pôde ser lida ou gravada."""


class FaceDB:
    """Embeddings dos rostos cadastrados, em um ``.npz`` com índice JSON.

    Cada pessoa tem **um** vetor: a média das capturas do cadastro, renormalizada.
    """

    def __init__(self, path: Path, dimension: int = 512) -> None:
        self.path = Path(path)
        self.dimension = dimension
        self._names: list[str] = []
        self._embeddings = np.zeros((0, dimension), dtype=np.float32)
        self.load()

    # -- persistência -------------------------------------------------------

    @property
    def index_path(self) -> Path:
        """O índice legível ao lado da base — para auditar o que está guardado."""
        return self.path.with_suffix(".json")

    def load(self) -> None:
        """Lê a base do disco. Uma base ausente é uma base vazia."""
        if not self.path.is_file():
            return
        try:
            with np.load(self.path, allow_pickle=False) as data:
                names = [str(name) for name in data["names"]]
                embeddings = np.asarray(data["embeddings"], dtype=np.float32)
        except (OSError, ValueError, KeyError) as error:
            raise FaceDBError(
                f"Não consegui ler a base de rostos em {self.path}: {error}"
            ) from error

        if embeddings.ndim != 2 or len(names) != len(embeddings):
            raise FaceDBError(f"A base de rostos em {self.path} está inconsistente.")
        self._names, self._embeddings = names, embeddings
        if embeddings.size:
            self.dimension = embeddings.shape[1]

    def save(self) -> None:
        """Grava a base de forma atômica e com permissão restrita."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        partial = self.path.with_suffix(self.path.suffix + ".part")
        try:
            with partial.open("wb") as handle:
                # np.savez acrescentaria ".npz" se recebesse o caminho: o arquivo
                # temporário viraria "faces.npz.part.npz" e o replace falharia.
                np.savez(
                    handle,
                    names=np.array(self._names, dtype=f"U{MAX_NAME_LENGTH}"),
                    embeddings=self._embeddings,
                )
            os.chmod(partial, FILE_MODE)
            os.replace(partial, self.path)
            self._write_index()
        except OSError as error:
            partial.unlink(missing_ok=True)
            raise FaceDBError(f"Não consegui gravar a base de rostos: {error}") from error

    def _write_index(self) -> None:
        """Índice em JSON: quem está cadastrado, sem expor nenhum vetor."""
        payload = {
            "schema": SCHEMA_VERSION,
            "dimension": self.dimension,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "names": sorted(self._names),
            "note": "Somente embeddings; nenhuma imagem é armazenada.",
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        os.chmod(self.index_path, FILE_MODE)

    # -- consulta -----------------------------------------------------------

    def names(self) -> list[str]:
        """Nomes cadastrados, em ordem alfabética."""
        return sorted(self._names)

    def __len__(self) -> int:
        return len(self._names)

    def __contains__(self, name: str) -> bool:
        return name in self._names

    def match(self, embedding: np.ndarray, threshold: float) -> tuple[str | None, float]:
        """Acha o rosto cadastrado mais próximo.

        Devolve ``(nome, distância)``, ou ``(None, distância)`` quando o mais
        próximo ainda está além do limiar — o caso "Desconhecido".
        """
        if not self._names:
            return None, float("inf")
        query = normalize(np.asarray(embedding, dtype=np.float32))
        distances = [cosine_distance(query, known) for known in self._embeddings]
        best = int(np.argmin(distances))
        distance = float(distances[best])
        return (self._names[best] if distance <= threshold else None), distance

    # -- escrita ------------------------------------------------------------

    def add(self, name: str, embedding: np.ndarray) -> None:
        """Cadastra (ou atualiza) uma pessoa. Grava em disco na hora."""
        name = name.strip()
        if not name:
            raise ValueError("O nome não pode ser vazio.")
        if len(name) > MAX_NAME_LENGTH:
            raise ValueError(f"O nome passa de {MAX_NAME_LENGTH} caracteres.")
        vector = normalize(np.asarray(embedding, dtype=np.float32)).reshape(1, -1)
        if self._embeddings.size and vector.shape[1] != self._embeddings.shape[1]:
            raise ValueError(
                f"O embedding tem {vector.shape[1]} dimensões, "
                f"mas a base usa {self._embeddings.shape[1]}."
            )

        if name in self._names:
            self._embeddings[self._names.index(name)] = vector[0]
        else:
            self._names.append(name)
            self._embeddings = (
                vector if not self._embeddings.size else np.vstack([self._embeddings, vector])
            )
        self.dimension = self._embeddings.shape[1]
        self.save()

    def delete(self, name: str) -> bool:
        """Apaga um cadastro — o direito ao esquecimento da LGPD.

        Devolve se havia algo para apagar.
        """
        if name not in self._names:
            return False
        index = self._names.index(name)
        del self._names[index]
        self._embeddings = np.delete(self._embeddings, index, axis=0)
        self.save()
        return True

    def clear(self) -> None:
        """Apaga tudo, inclusive os arquivos em disco."""
        self._names = []
        self._embeddings = np.zeros((0, self.dimension), dtype=np.float32)
        self.path.unlink(missing_ok=True)
        self.index_path.unlink(missing_ok=True)
