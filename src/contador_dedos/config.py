"""Configuração da aplicação e a CLI que a produz."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .vision.embedder import DEFAULT_THRESHOLD as DEFAULT_FACE_THRESHOLD

#: Onde o modelo fica em disco (gitignorado — ver `.gitignore`).
#: `parents[2]` sobe de `src/contador_dedos/config.py` até a raiz do repositório;
#: o projeto é instalado em modo editável, então esse caminho vale também para o
#: comando `contador-dedos`.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = _PROJECT_ROOT / "models" / "hand_landmarker.task"
#: Base de rostos: local, fora do versionamento, com acesso restrito ao usuário.
DEFAULT_FACES_DB = _PROJECT_ROOT / "faces" / "faces.npz"


@dataclass(frozen=True)
class AppConfig:
    """Parâmetros de execução — substitui os valores hardcoded."""

    camera_index: int = 0
    max_hands: int = 2
    detection_confidence: float = 0.5
    tracking_confidence: float = 0.5
    mirror: bool = True
    smooth_window: int = 5
    model_path: Path = DEFAULT_MODEL_PATH
    faces_db: Path = DEFAULT_FACES_DB
    face_threshold: float = DEFAULT_FACE_THRESHOLD

    @property
    def models_dir(self) -> Path:
        """Onde ficam todos os modelos baixados."""
        return self.model_path.parent


def parse_args(argv: Sequence[str] | None = None) -> AppConfig:
    """Traduz os argumentos de linha de comando em um :class:`AppConfig`."""
    defaults = AppConfig()
    parser = argparse.ArgumentParser(
        prog="contador-dedos",
        description="Conta os dedos levantados em tempo real usando a webcam.",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=defaults.camera_index,
        metavar="N",
        help="índice da câmera (padrão: %(default)s)",
    )
    parser.add_argument(
        "--max-hands",
        type=int,
        default=defaults.max_hands,
        metavar="N",
        help="número máximo de mãos detectadas (padrão: %(default)s)",
    )
    parser.add_argument(
        "--detection-confidence",
        type=float,
        default=defaults.detection_confidence,
        metavar="F",
        help="confiança mínima de detecção, entre 0 e 1 (padrão: %(default)s)",
    )
    parser.add_argument(
        "--tracking-confidence",
        type=float,
        default=defaults.tracking_confidence,
        metavar="F",
        help="confiança mínima de rastreamento, entre 0 e 1 (padrão: %(default)s)",
    )
    parser.add_argument(
        "--smooth-window",
        type=int,
        default=defaults.smooth_window,
        metavar="N",
        help="frames usados para suavizar a contagem (padrão: %(default)s)",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=defaults.model_path,
        metavar="ARQUIVO",
        help="caminho do hand_landmarker.task (baixado se faltar)",
    )
    parser.add_argument(
        "--faces-db",
        type=Path,
        default=defaults.faces_db,
        metavar="ARQUIVO",
        help="base local de rostos cadastrados (padrão: %(default)s)",
    )
    parser.add_argument(
        "--face-threshold",
        type=float,
        default=defaults.face_threshold,
        metavar="F",
        help="distância máxima para reconhecer um rosto; menor = mais rigor "
        "(padrão: %(default)s)",
    )
    mirror = parser.add_mutually_exclusive_group()
    mirror.add_argument(
        "--mirror",
        dest="mirror",
        action="store_true",
        help="espelha a imagem, como um espelho (padrão)",
    )
    mirror.add_argument(
        "--no-mirror",
        dest="mirror",
        action="store_false",
        help="mostra a imagem crua da câmera, sem espelhar",
    )
    parser.set_defaults(mirror=defaults.mirror)

    args = parser.parse_args(argv)
    if args.camera < 0:
        parser.error("--camera precisa ser >= 0.")
    if args.max_hands < 1:
        parser.error("--max-hands precisa ser >= 1.")
    if args.smooth_window < 1:
        parser.error("--smooth-window precisa ser >= 1.")
    if not 0.0 < args.face_threshold <= 2.0:
        parser.error("--face-threshold precisa estar entre 0 (exclusivo) e 2.")
    for name, value in (
        ("--detection-confidence", args.detection_confidence),
        ("--tracking-confidence", args.tracking_confidence),
    ):
        if not 0.0 <= value <= 1.0:
            parser.error(f"{name} precisa estar entre 0 e 1.")

    return AppConfig(
        camera_index=args.camera,
        max_hands=args.max_hands,
        detection_confidence=args.detection_confidence,
        tracking_confidence=args.tracking_confidence,
        mirror=args.mirror,
        smooth_window=args.smooth_window,
        model_path=args.model,
        faces_db=args.faces_db,
        face_threshold=args.face_threshold,
    )
