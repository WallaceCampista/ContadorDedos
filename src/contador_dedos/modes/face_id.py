"""Modo "Rosto (ID)": reconhece rostos cadastrados localmente.

O fluxo segue a Seção 5.2 do plano: reconhecer → *cadastrar* passa por uma tela
de **consentimento** explícita, depois nome, depois captura. E há uma tela de
gerenciamento para **excluir** um cadastro — o direito ao esquecimento não é um
detalhe de implementação, é requisito.

Os recursos pesados (detector de rosto e ArcFace) são criados **na primeira vez
que o modo é aberto**, e não no início do app: quem nunca entra aqui não paga o
download do modelo.
"""

from __future__ import annotations

from enum import Enum, auto

import cv2
import numpy as np

from ..core.pipeline import ValueSmoother
from ..storage.faces_db import MAX_NAME_LENGTH, FaceDB, FaceDBError
from ..ui.theme import COLOR_ACCENT, COLOR_MUTED, COLOR_TEXT
from ..ui.widgets import (
    Rect,
    draw_button,
    draw_center_message,
    draw_centered_text,
    draw_panel,
    draw_text,
    draw_veil,
    hud_scale,
    text_size,
)
from ..vision.embedder import ARCFACE_FILENAME, DEFAULT_THRESHOLD, ArcFaceEmbedder
from ..vision.faces import FACE_MODEL_FILENAME, FaceTracker, align_face
from ..vision.model import ModelError
from .base import Mode

#: Quantos frames com rosto são capturados em um cadastro.
ENROLL_FRAMES = 12
#: Por quantos frames uma mensagem de status fica na tela.
MESSAGE_FRAMES = 60

UNKNOWN_NAME = "Desconhecido"

CONSENT_TITLE = "Cadastro de rosto — o que você está autorizando"
CONSENT_LINES = (
    "Dado biométrico facial é dado pessoal SENSÍVEL (LGPD, Art. 5º, II).",
    "",
    "O QUE é guardado: um vetor numérico (embedding) calculado do seu rosto.",
    "Nenhuma foto é gravada, e o vetor não reconstrói a sua imagem.",
    "",
    "ONDE: somente neste computador, em um arquivo local com acesso",
    "restrito ao seu usuário. Nada é enviado para a internet.",
    "",
    "COMO EXCLUIR: no botão Gerenciar deste modo, a qualquer momento.",
    "A exclusão é imediata e definitiva.",
)
CONSENT_ACCEPT = "Aceito e quero cadastrar"
CONSENT_CANCEL = "Cancelar"


class Stage(Enum):
    """As telas por dentro do modo."""

    RECOGNIZING = auto()
    CONSENT = auto()
    NAMING = auto()
    CAPTURING = auto()
    MANAGING = auto()


class FaceId(Mode):
    """Reconhece rostos cadastrados e cuida do cadastro e da exclusão."""

    name = "Rosto (ID)"
    icon = "🙂"
    hint = "ESC volta ao menu  •  Q encerra"

    def __init__(
        self,
        db: FaceDB,
        tracker_factory,
        embedder_factory,
        threshold: float = DEFAULT_THRESHOLD,
        smooth_window: int = 5,
    ) -> None:
        self.db = db
        self.threshold = threshold
        self._tracker_factory = tracker_factory
        self._embedder_factory = embedder_factory
        self._tracker = None
        self._embedder = None
        self._error: str | None = None
        self._announced = False

        self.stage = Stage.RECOGNIZING
        self._buttons: list[tuple[Rect, str]] = []
        self._hovered: str | None = None
        self._pending: str | None = None
        self._typed = ""
        self._captured: list[np.ndarray] = []
        self._message: str | None = None
        self._message_frames = 0
        self._smoother = ValueSmoother(smooth_window)

    @classmethod
    def from_config(cls, config, _hand_tracker=None) -> FaceId:
        models = config.models_dir
        return cls(
            db=FaceDB(config.faces_db),
            tracker_factory=lambda: FaceTracker(models / FACE_MODEL_FILENAME),
            embedder_factory=lambda: ArcFaceEmbedder(models / ARCFACE_FILENAME),
            threshold=config.face_threshold,
            smooth_window=config.smooth_window,
        )

    # -- ciclo de vida ------------------------------------------------------

    @property
    def ready(self) -> bool:
        return self._tracker is not None and self._embedder is not None

    def _prepare(self) -> None:
        """Cria detector e embedder. Pode baixar modelos — por isso é tardio."""
        try:
            self._tracker = self._tracker_factory()
            self._embedder = self._embedder_factory()
        except (ModelError, OSError, ImportError) as error:
            self._error = str(error)

    def close(self) -> None:
        if self._tracker is not None:
            self._tracker.close()
            self._tracker = None

    # -- entrada ------------------------------------------------------------

    def on_mouse(self, event: int, x: int, y: int) -> None:
        self._hovered = None
        for rect, action in self._buttons:
            if rect.contains(x, y):
                self._hovered = action
                if event == cv2.EVENT_LBUTTONDOWN:
                    self._pending = action
                return

    def on_key(self, key: int) -> bool:
        """Enquanto se digita um nome, o modo consome todas as teclas."""
        if self.stage is not Stage.NAMING:
            return False
        if key in (13, 10):  # Enter
            self._pending = "confirm-name"
        elif key in (8, 127):  # Backspace
            self._typed = self._typed[:-1]
        elif key == 27:  # ESC cancela o cadastro, sem sair do modo
            self._pending = "cancel"
        elif 32 <= key < 127 and len(self._typed) < MAX_NAME_LENGTH:
            self._typed += chr(key)
        return True

    # -- ações --------------------------------------------------------------

    def _apply_pending(self) -> None:
        action, self._pending = self._pending, None
        if action is None:
            return
        if action == "enroll":
            self.stage = Stage.CONSENT
        elif action == "accept":
            self._typed = ""
            self.stage = Stage.NAMING
        elif action == "cancel":
            self._typed = ""
            self._captured.clear()
            self.stage = Stage.RECOGNIZING
        elif action == "confirm-name":
            if self._typed.strip():
                self._captured.clear()
                self.stage = Stage.CAPTURING
            else:
                self._notify("Digite um nome para continuar.")
        elif action == "manage":
            self.stage = Stage.MANAGING
        elif action == "back":
            self.stage = Stage.RECOGNIZING
        elif action.startswith("delete:"):
            self._delete(action[len("delete:") :])

    def _delete(self, name: str) -> None:
        try:
            apagado = self.db.delete(name)
        except FaceDBError as error:
            self._notify(str(error))
            return
        self._notify(f"'{name}' excluído." if apagado else f"'{name}' não estava cadastrado.")

    def _notify(self, message: str) -> None:
        self._message, self._message_frames = message, MESSAGE_FRAMES

    # -- processamento ------------------------------------------------------

    def process(self, frame, timestamp_ms: int = 0):
        height = frame.shape[0]
        scale = hud_scale(height)
        self._buttons = []
        self._apply_pending()

        if self._error is not None:
            draw_veil(frame)
            draw_center_message(frame, "Reconhecimento facial indisponível", scale)
            self._draw_footer_note(frame, scale, self._error[:90])
            return frame

        if not self.ready:
            if not self._announced:
                # Mostra o aviso um frame ANTES de bloquear no download.
                self._announced = True
                draw_veil(frame)
                draw_center_message(frame, "Preparando… (1ª vez baixa ~122 MB)", scale)
                return frame
            self._prepare()
            return frame

        faces = self._tracker.detect(frame, timestamp_ms)
        if self.stage is Stage.CAPTURING:
            self._capture(frame, faces, scale)
        elif self.stage is Stage.RECOGNIZING:
            self._recognize(frame, faces, scale)

        if self.stage is Stage.CONSENT:
            self._draw_consent(frame, scale)
        elif self.stage is Stage.NAMING:
            self._draw_naming(frame, scale)
        elif self.stage is Stage.MANAGING:
            self._draw_managing(frame, scale)
        elif self.stage is Stage.RECOGNIZING:
            self._draw_actions(frame, scale)

        self._draw_message(frame, scale)
        return frame

    def _embed(self, frame, face) -> np.ndarray | None:
        aligned = align_face(frame, face)
        if aligned is None:
            return None
        return self._embedder.embed(aligned)

    def _recognize(self, frame, faces, scale: float) -> None:
        nomes = []
        for face in faces:
            embedding = self._embed(frame, face)
            if embedding is None:
                continue
            nome, distancia = self.db.match(embedding, self.threshold)
            nomes.append(nome)
            self._draw_face(frame, face, nome, distancia, scale)
        if not faces:
            draw_center_message(frame, "Nenhum rosto detectado", scale)
        elif not self.db.names():
            draw_center_message(frame, "Nenhum rosto cadastrado ainda", scale)
        self._smoother.update(nomes[0] if nomes else None)

    def _capture(self, frame, faces, scale: float) -> None:
        if len(faces) != 1:
            aviso = "Mostre apenas um rosto" if faces else "Nenhum rosto detectado"
            draw_center_message(frame, aviso, scale)
        else:
            embedding = self._embed(frame, faces[0])
            if embedding is not None:
                self._captured.append(embedding)
            self._draw_face(frame, faces[0], self._typed, 0.0, scale, capturing=True)

        progresso = f"Capturando {len(self._captured)}/{ENROLL_FRAMES}"
        draw_centered_text(
            frame, progresso, frame.shape[1] // 2, int(40 * scale), 0.6 * scale, COLOR_ACCENT
        )
        self._add_button(frame, "cancel", "Cancelar", scale, bottom=True)

        if len(self._captured) >= ENROLL_FRAMES:
            self._finish_enrollment()

    def _finish_enrollment(self) -> None:
        media = np.mean(np.stack(self._captured), axis=0)
        nome = self._typed.strip()
        try:
            self.db.add(nome, media)
        except (FaceDBError, ValueError) as error:
            self._notify(str(error))
        else:
            self._notify(f"'{nome}' cadastrado a partir de {len(self._captured)} capturas.")
        self._captured.clear()
        self._typed = ""
        self.stage = Stage.RECOGNIZING

    # -- desenho ------------------------------------------------------------

    def _draw_face(self, frame, face, nome, distancia, scale, capturing=False) -> None:
        x, y, width, height = face.box
        cor = COLOR_ACCENT if (nome or capturing) else COLOR_MUTED
        cv2.rectangle(frame, (x, y), (x + width, y + height), cor, max(2, int(2 * scale)))
        rotulo = nome or UNKNOWN_NAME
        if not capturing and nome:
            rotulo = f"{rotulo}  ({distancia:.2f})"
        draw_text(
            frame,
            rotulo,
            (x, max(y - int(8 * scale), int(14 * scale))),
            0.6 * scale,
            cor,
            max(1, int(scale)),
        )

    def _add_button(self, frame, action: str, label: str, scale: float, bottom=False, index=0):
        height, width = frame.shape[:2]
        largura = text_size(label, 0.5 * scale, max(1, int(scale)))[0] + int(24 * scale)
        altura = int(30 * scale)
        x = width - largura - int(14 * scale)
        y = height - int((54 + index * 40) * scale) if bottom else int((14 + index * 40) * scale)
        rect = Rect(x, y, largura, altura)
        draw_button(frame, rect, label, scale, hovered=self._hovered == action)
        self._buttons.append((rect, action))

    def _draw_actions(self, frame, scale: float) -> None:
        self._add_button(frame, "enroll", "Cadastrar rosto", scale, bottom=True, index=0)
        self._add_button(
            frame, "manage", f"Gerenciar ({len(self.db)})", scale, bottom=True, index=1
        )

    def _dialog_rect(self, frame, scale: float, lines: int) -> Rect:
        height, width = frame.shape[:2]
        largura = min(int(560 * scale), width - int(40 * scale))
        altura = int((90 + lines * 22) * scale)
        return Rect((width - largura) // 2, (height - altura) // 2, largura, altura)

    def _draw_consent(self, frame, scale: float) -> None:
        draw_veil(frame)
        painel = self._dialog_rect(frame, scale, len(CONSENT_LINES) + 2)
        draw_panel(frame, painel, alpha=0.94)
        centro = painel.center[0]
        draw_centered_text(
            frame,
            CONSENT_TITLE,
            centro,
            painel.y + int(30 * scale),
            0.6 * scale,
            COLOR_ACCENT,
            max(1, int(scale)),
        )
        y = painel.y + int(58 * scale)
        for linha in CONSENT_LINES:
            draw_text(
                frame,
                linha,
                (painel.x + int(20 * scale), y),
                0.42 * scale,
                COLOR_TEXT,
                max(1, int(scale)),
            )
            y += int(22 * scale)

        largura = int(230 * scale)
        botao_y = painel.bottom - int(44 * scale)
        aceitar = Rect(centro - largura - int(8 * scale), botao_y, largura, int(32 * scale))
        cancelar = Rect(centro + int(8 * scale), botao_y, int(140 * scale), int(32 * scale))
        draw_button(frame, aceitar, CONSENT_ACCEPT, scale, hovered=self._hovered == "accept")
        draw_button(frame, cancelar, CONSENT_CANCEL, scale, hovered=self._hovered == "cancel")
        self._buttons += [(aceitar, "accept"), (cancelar, "cancel")]

    def _draw_naming(self, frame, scale: float) -> None:
        draw_veil(frame)
        painel = self._dialog_rect(frame, scale, 3)
        draw_panel(frame, painel, alpha=0.94)
        centro = painel.center[0]
        draw_centered_text(
            frame,
            "Nome de quem está sendo cadastrado",
            centro,
            painel.y + int(34 * scale),
            0.55 * scale,
            COLOR_ACCENT,
            max(1, int(scale)),
        )
        campo = Rect(
            painel.x + int(30 * scale),
            painel.y + int(52 * scale),
            painel.width - int(60 * scale),
            int(38 * scale),
        )
        draw_panel(frame, campo, alpha=0.9)
        draw_text(
            frame,
            (self._typed or "") + "_",
            (campo.x + int(10 * scale), campo.y + int(26 * scale)),
            0.6 * scale,
            COLOR_TEXT,
            max(1, int(scale)),
        )
        draw_centered_text(
            frame,
            "Enter confirma  •  ESC cancela",
            centro,
            painel.bottom - int(18 * scale),
            0.42 * scale,
            COLOR_MUTED,
        )

    def _draw_managing(self, frame, scale: float) -> None:
        draw_veil(frame)
        nomes = self.db.names()
        painel = self._dialog_rect(frame, scale, max(len(nomes), 1) + 2)
        draw_panel(frame, painel, alpha=0.94)
        centro = painel.center[0]
        draw_centered_text(
            frame,
            "Rostos cadastrados",
            centro,
            painel.y + int(30 * scale),
            0.6 * scale,
            COLOR_ACCENT,
            max(1, int(scale)),
        )

        y = painel.y + int(60 * scale)
        for nome in nomes:
            draw_text(
                frame,
                nome,
                (painel.x + int(24 * scale), y + int(16 * scale)),
                0.5 * scale,
                COLOR_TEXT,
                max(1, int(scale)),
            )
            botao = Rect(painel.right - int(120 * scale), y, int(96 * scale), int(26 * scale))
            acao = f"delete:{nome}"
            draw_button(frame, botao, "Excluir", scale, hovered=self._hovered == acao)
            self._buttons.append((botao, acao))
            y += int(34 * scale)
        if not nomes:
            draw_centered_text(
                frame,
                "Nenhum rosto cadastrado",
                centro,
                y + int(16 * scale),
                0.5 * scale,
                COLOR_MUTED,
            )

        voltar = Rect(
            centro - int(60 * scale),
            painel.bottom - int(42 * scale),
            int(120 * scale),
            int(30 * scale),
        )
        draw_button(frame, voltar, "Voltar", scale, hovered=self._hovered == "back")
        self._buttons.append((voltar, "back"))

    def _draw_message(self, frame, scale: float) -> None:
        if self._message is None:
            return
        self._message_frames -= 1
        if self._message_frames <= 0:
            self._message = None
            return
        self._draw_footer_note(frame, scale, self._message)

    def _draw_footer_note(self, frame, scale: float, texto: str) -> None:
        height, width = frame.shape[:2]
        draw_centered_text(
            frame,
            texto,
            width // 2,
            height - int(52 * scale),
            0.45 * scale,
            COLOR_ACCENT,
            max(1, int(scale)),
        )
