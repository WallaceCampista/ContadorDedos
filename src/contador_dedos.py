"""Contador de Dedos — detecta mãos na webcam e conta os dedos levantados.

O módulo separa a **lógica pura** (``count_fingers`` e auxiliares, testáveis sem
webcam) da **camada de I/O** (captura, desenho e loop principal), preparando o
terreno para a estrutura de pacote descrita no ``Plano_melhoria.md``.

A detecção usa a **MediaPipe Tasks API** (``HandLandmarker``), que substituiu a
API legada ``mp.solutions`` — removida no MediaPipe 0.10.35. Ela depende do
modelo ``hand_landmarker.task``, baixado sob demanda para ``models/`` (fora do
versionamento) na primeira execução ou pelo ``setup.sh``.

Uso:
    python src/main.py [--camera 0] [--max-hands 2] [--no-mirror]

Encerre a janela com **Q** ou **ESC**.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, deque
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    HandLandmarksConnections,
    RunningMode,
    drawing_styles,
    drawing_utils,
)

# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------

#: Onde o modelo fica em disco (gitignorado — ver `.gitignore`).
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
#: Confere a integridade do download (a URL é versionada, então é estável).
MODEL_SHA256 = "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1"

# ---------------------------------------------------------------------------
# Landmarks — nomes no lugar dos números mágicos
# ---------------------------------------------------------------------------

#: Pontas do indicador, médio, anelar e mínimo.
FINGER_TIP_IDS: tuple[int, ...] = (8, 12, 16, 20)
#: A articulação PIP de cada dedo fica dois índices antes da ponta.
PIP_OFFSET = 2
#: Ponta e articulação interfalângica do polegar.
THUMB_TIP, THUMB_IP = 4, 3

#: Um landmark já convertido para pixels da imagem.
Point = tuple[int, int]

# ---------------------------------------------------------------------------
# Aparência
# ---------------------------------------------------------------------------

WINDOW_NAME = "Contador de Dedos"
FONT = cv2.FONT_HERSHEY_SIMPLEX

COLOR_TEXT = (255, 255, 255)
COLOR_OUTLINE = (0, 0, 0)
COLOR_TOTAL = (0, 0, 255)
COLOR_HINT = (200, 200, 200)

#: Altura de referência para a qual os tamanhos do HUD foram desenhados.
HUD_REFERENCE_HEIGHT = 480

KEYS_QUIT = (ord("q"), ord("Q"), 27)  # Q ou ESC
#: Quantos frames inválidos seguidos toleramos antes de desistir da câmera.
MAX_READ_FAILURES = 30


class CameraError(RuntimeError):
    """A câmera não pôde ser aberta ou parou de entregar frames."""


class ModelError(RuntimeError):
    """O modelo do MediaPipe não está disponível e não pôde ser obtido."""


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Lógica pura — sem OpenCV, sem câmera, testável isoladamente
# ---------------------------------------------------------------------------


def is_thumb_extended(landmarks: Sequence[Point], handedness: str) -> bool:
    """Diz se o polegar está estendido.

    ``handedness`` é o rótulo devolvido pelo MediaPipe (``"Left"``/``"Right"``)
    **para o mesmo frame** de onde vieram os landmarks. O MediaPipe classifica
    a lateralidade assumindo uma imagem espelhada, e essa mesma convenção fixa
    o sentido em que o polegar aponta no eixo X — por isso a regra abaixo vale
    tanto com quanto sem ``cv2.flip`` (ver ``count_fingers``).
    """
    if handedness == "Right":
        return landmarks[THUMB_TIP][0] > landmarks[THUMB_IP][0]
    return landmarks[THUMB_TIP][0] < landmarks[THUMB_IP][0]


def count_fingers(landmarks: Sequence[Point], handedness: str) -> int:
    """Conta quantos dedos estão levantados em uma mão.

    Args:
        landmarks: os 21 landmarks da mão em pixels, na ordem do MediaPipe.
        handedness: ``"Left"`` ou ``"Right"``, como reportado pelo MediaPipe
            para o frame processado.

    Os quatro dedos longos contam como levantados quando a ponta está *acima*
    da articulação PIP (Y menor, pois o eixo cresce para baixo). O polegar usa
    o eixo X, porque ele se abre lateralmente — daí depender da lateralidade.

    Como o rótulo do MediaPipe e a geometria da imagem seguem a mesma convenção
    de espelhamento, o resultado independe de o frame ter sido espelhado ou não;
    o que muda é apenas a qual mão real aquele rótulo corresponde.
    """
    if len(landmarks) <= max(FINGER_TIP_IDS):
        raise ValueError(f"Esperava 21 landmarks, recebi {len(landmarks)}.")

    count = 1 if is_thumb_extended(landmarks, handedness) else 0
    for tip in FINGER_TIP_IDS:
        if landmarks[tip][1] < landmarks[tip - PIP_OFFSET][1]:
            count += 1
    return count


def real_hand(handedness: str, mirrored: bool) -> str:
    """Converte o rótulo do MediaPipe na mão real da pessoa.

    O MediaPipe assume imagem espelhada: com ``cv2.flip`` aplicado o rótulo já
    corresponde à mão real; sem espelhamento, ele vem trocado.
    """
    if mirrored:
        return handedness
    return "Left" if handedness == "Right" else "Right"


class CountSmoother:
    """Anti-flicker: devolve o valor mais frequente das últimas N leituras.

    ``None`` representa "mão ausente" e também entra na janela, de modo que o
    contador some suavemente quando a mão sai do quadro.
    """

    def __init__(self, window: int = 5) -> None:
        if window < 1:
            raise ValueError("A janela de suavização precisa ser >= 1.")
        self._history: deque[int | None] = deque(maxlen=window)

    def update(self, value: int | None) -> int | None:
        self._history.append(value)
        return Counter(self._history).most_common(1)[0][0]


class FpsMeter:
    """FPS com média exponencial, para o número não tremer na tela."""

    def __init__(self, smoothing: float = 0.9) -> None:
        self._smoothing = smoothing
        self._fps = 0.0
        self._last: float | None = None

    def tick(self, now: float | None = None) -> float:
        now = time.perf_counter() if now is None else now
        if self._last is not None:
            elapsed = now - self._last
            if elapsed > 0:
                instant = 1.0 / elapsed
                self._fps = (
                    instant
                    if self._fps == 0.0
                    else self._smoothing * self._fps + (1 - self._smoothing) * instant
                )
        self._last = now
        return self._fps


def landmarks_to_pixels(landmarks, width: int, height: int) -> list[Point]:
    """Converte landmarks normalizados do MediaPipe para pixels da imagem."""
    return [(int(landmark.x * width), int(landmark.y * height)) for landmark in landmarks]


# ---------------------------------------------------------------------------
# Desenho
# ---------------------------------------------------------------------------


def draw_text(
    img,
    text: str,
    org: Point,
    scale: float = 0.6,
    color: tuple[int, int, int] = COLOR_TEXT,
    thickness: int = 1,
) -> None:
    """Escreve com contorno preto, para o texto não sumir em fundos claros."""
    cv2.putText(img, text, org, FONT, scale, COLOR_OUTLINE, thickness + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, FONT, scale, color, thickness, cv2.LINE_AA)


def hud_scale(height: int) -> float:
    """Fator de escala do HUD, para o texto ficar legível em qualquer resolução.

    Os tamanhos foram desenhados para 480px de altura; em uma webcam 1080p o
    HUD sem escala vira um detalhe ilegível no canto.
    """
    return max(height / HUD_REFERENCE_HEIGHT, 0.5)


def draw_counter(
    img,
    label: str,
    value: int | None,
    x: int,
    scale: float,
    color: tuple[int, int, int] = COLOR_TEXT,
) -> None:
    """Desenha um rótulo e, logo abaixo, o valor daquele contador."""
    draw_text(img, label, (x, int(30 * scale)), 0.5 * scale, thickness=max(1, int(scale)))
    draw_text(
        img,
        "-" if value is None else str(value),
        (x + int(20 * scale), int(80 * scale)),
        2.0 * scale,
        color,
        max(2, int(5 * scale)),
    )


def draw_hud(img, counts: dict[str, int | None], fps: float, mirrored: bool) -> None:
    """Desenha contadores, total, FPS e a barra de dicas sobre o frame."""
    height, width = img.shape[:2]
    scale = hud_scale(height)

    # Cada painel fica do lado da tela em que aquela mão realmente aparece.
    left_hand, right_hand = ("Left", "Right") if mirrored else ("Right", "Left")
    draw_counter(
        img, "Esquerda" if mirrored else "Direita", counts[left_hand], int(10 * scale), scale
    )
    draw_counter(
        img,
        "Direita" if mirrored else "Esquerda",
        counts[right_hand],
        width - int(130 * scale),
        scale,
    )

    total = sum(value for value in counts.values() if value is not None)
    draw_counter(img, "Total", total, width // 2 - int(30 * scale), scale, COLOR_TOTAL)

    footer_y = height - int(12 * scale)
    footer_scale = 0.5 * scale
    thickness = max(1, int(scale))
    draw_text(
        img, f"{fps:4.1f} FPS", (int(10 * scale), footer_y), footer_scale, COLOR_HINT, thickness
    )
    hint = "Q ou ESC para sair"
    (hint_width, _), _ = cv2.getTextSize(hint, FONT, footer_scale, thickness)
    draw_text(
        img,
        hint,
        (width - hint_width - int(10 * scale), footer_y),
        footer_scale,
        COLOR_HINT,
        thickness,
    )


# ---------------------------------------------------------------------------
# Modelo — download sob demanda
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(destination: Path, url: str = MODEL_URL) -> None:
    """Baixa o modelo para ``destination``, validando a integridade.

    Escreve primeiro em um arquivo temporário e só então renomeia, para que uma
    interrupção no meio do caminho nunca deixe um modelo truncado no lugar.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    print(f"Baixando o modelo de detecção de mãos (~7,5 MB) para {destination}…")
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
        print("\r  100%")
    except (urllib.error.URLError, OSError) as error:
        partial.unlink(missing_ok=True)
        raise ModelError(
            f"Não consegui baixar o modelo de {url}: {error}\n"
            f"Baixe manualmente e salve em {destination}."
        ) from error

    actual = _sha256(partial)
    if actual != MODEL_SHA256:
        partial.unlink(missing_ok=True)
        raise ModelError(
            "O modelo baixado não confere com o hash esperado "
            f"(esperado {MODEL_SHA256}, obtido {actual}). "
            "O arquivo pode ter sido republicado na origem ou corrompido no caminho."
        )
    os.replace(partial, destination)


def ensure_model(path: Path, allow_download: bool = True) -> Path:
    """Garante que o modelo exista em ``path``, baixando-o se necessário."""
    if path.is_file():
        return path
    if not allow_download:
        raise ModelError(f"Modelo não encontrado em {path}.")
    download_model(path)
    return path


# ---------------------------------------------------------------------------
# Camada de I/O
# ---------------------------------------------------------------------------


@contextmanager
def open_camera(index: int) -> Iterator[cv2.VideoCapture]:
    """Abre a câmera validando o acesso e garantindo a liberação no fim."""
    video = cv2.VideoCapture(index)
    if not video.isOpened():
        video.release()
        raise CameraError(
            f"Não consegui abrir a câmera {index}. "
            "Verifique se ela está conectada, se outro programa não está usando-a "
            "e se o terminal tem permissão de acesso à câmera."
        )
    try:
        yield video
    finally:
        video.release()


def create_landmarker(config: AppConfig) -> HandLandmarker:
    """Instancia o ``HandLandmarker`` da Tasks API no modo de vídeo."""
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(config.model_path)),
        running_mode=RunningMode.VIDEO,
        num_hands=config.max_hands,
        min_hand_detection_confidence=config.detection_confidence,
        min_hand_presence_confidence=config.detection_confidence,
        min_tracking_confidence=config.tracking_confidence,
    )
    return HandLandmarker.create_from_options(options)


def should_quit(key: int) -> bool:
    """Diz se a tecla pressionada encerra o app."""
    return key in KEYS_QUIT


def window_was_closed() -> bool:
    """Detecta o fechamento da janela pelo botão do sistema."""
    try:
        return cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def run(config: AppConfig) -> None:
    """Loop principal: captura → detecção → anotação → render."""
    ensure_model(config.model_path)

    smoothers = {
        "Left": CountSmoother(config.smooth_window),
        "Right": CountSmoother(config.smooth_window),
    }
    fps_meter = FpsMeter()
    landmark_style = drawing_styles.get_default_hand_landmarks_style()
    connection_style = drawing_styles.get_default_hand_connections_style()
    failures = 0
    started = time.perf_counter()
    last_timestamp_ms = -1

    with open_camera(config.camera_index) as video, create_landmarker(config) as landmarker:
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        try:
            while True:
                check, frame = video.read()
                if not check or frame is None:
                    failures += 1
                    if failures >= MAX_READ_FAILURES:
                        raise CameraError(
                            f"A câmera {config.camera_index} parou de entregar frames."
                        )
                    continue
                failures = 0

                if config.mirror:
                    frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]

                # detect_for_video exige timestamps estritamente crescentes.
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                last_timestamp_ms = max(elapsed_ms, last_timestamp_ms + 1)
                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                )
                result = landmarker.detect_for_video(image, last_timestamp_ms)

                counts: dict[str, int | None] = {"Left": None, "Right": None}
                for hand_landmarks, handedness in zip(result.hand_landmarks, result.handedness):
                    drawing_utils.draw_landmarks(
                        frame,
                        hand_landmarks,
                        HandLandmarksConnections.HAND_CONNECTIONS,
                        landmark_style,
                        connection_style,
                    )
                    label = handedness[0].category_name
                    points = landmarks_to_pixels(hand_landmarks, width, height)
                    counts[real_hand(label, config.mirror)] = count_fingers(points, label)

                smoothed = {hand: smoothers[hand].update(value) for hand, value in counts.items()}
                draw_hud(frame, smoothed, fps_meter.tick(), config.mirror)

                cv2.imshow(WINDOW_NAME, frame)
                if should_quit(cv2.waitKey(1) & 0xFF) or window_was_closed():
                    break
        finally:
            cv2.destroyAllWindows()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada: devolve 0 em caso de sucesso, 1 em caso de erro."""
    config = parse_args(argv)
    try:
        run(config)
    except (CameraError, ModelError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
