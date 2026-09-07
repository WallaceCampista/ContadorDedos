"""Tradução dos rótulos da interface.

O **texto em português é a própria chave**: `t("Esquerda")` devolve `"Left"` em
inglês e `"Esquerda"` em português. Isso mantém o código legível — dá para ler a
tela olhando a fonte — e faz uma chave sem tradução degradar para o português em
vez de estourar.

Há um teste que varre o código atrás de `t("…")` e cobra tradução para cada um,
para nenhuma string nova passar despercebida.
"""

from __future__ import annotations

#: Idiomas suportados. O primeiro é o do código-fonte.
LANGUAGES = ("pt", "en")
DEFAULT_LANGUAGE = "pt"

#: Português → inglês. Marcadores como `{n}` são preservados nos dois lados.
CATALOG: dict[str, str] = {
    # --- menu ---
    "Escolha o que deseja fazer": "Choose what to do",
    "Clique em um card  •  Q encerra": "Click a card  •  Q quits",
    "Sair": "Quit",
    "← Voltar": "← Back",
    "Voltar": "Back",
    # --- modos ---
    "Contar Dedos": "Count Fingers",
    "Gestos": "Gestures",
    "Libras": "Libras",
    "Rosto (ID)": "Face ID",
    "ESC volta ao menu  •  Q encerra": "ESC back to menu  •  Q quits",
    # --- contagem ---
    "Esquerda": "Left",
    "Direita": "Right",
    "Total": "Total",
    "Nenhuma mão detectada": "No hand detected",
    # --- gestos ---
    "Joinha": "Thumbs up",
    "Paz": "Peace",
    "OK": "OK",
    "Mão aberta": "Open hand",
    "Mão fechada": "Closed fist",
    "Mostre a mão para a câmera": "Show your hand to the camera",
    # --- libras ---
    "um": "one",
    "dois": "two",
    "três": "three",
    "quatro": "four",
    "cinco": "five",
    "Reconhece 1 a 5 — 0 e 6 a 10 ainda não": "Recognizes 1 to 5 — 0 and 6 to 10 not yet",
    # --- rosto ---
    "Desconhecido": "Unknown",
    "Cadastrar rosto": "Enroll face",
    "Gerenciar ({n})": "Manage ({n})",
    "Excluir": "Delete",
    "Cancelar": "Cancel",
    "Rostos cadastrados": "Enrolled faces",
    "Nenhum rosto cadastrado": "No face enrolled",
    "Nenhum rosto cadastrado ainda": "No face enrolled yet",
    "Nenhum rosto detectado": "No face detected",
    "Mostre apenas um rosto": "Show only one face",
    "Capturando {feitas}/{total}": "Capturing {feitas}/{total}",
    "Nome de quem está sendo cadastrado": "Name of the person being enrolled",
    "Enter confirma  •  ESC cancela": "Enter confirms  •  ESC cancels",
    "Digite um nome para continuar.": "Type a name to continue.",
    "Preparando… (1ª vez baixa ~122 MB)": "Preparing… (first run downloads ~122 MB)",
    "Reconhecimento facial indisponível": "Face recognition unavailable",
    "'{nome}' cadastrado a partir de {n} capturas.": "'{nome}' enrolled from {n} captures.",
    "'{nome}' excluído.": "'{nome}' deleted.",
    "'{nome}' não estava cadastrado.": "'{nome}' was not enrolled.",
    "Cadastro de rosto — o que você está autorizando": "Face enrollment — what you are authorizing",
    "Aceito e quero cadastrar": "I accept and want to enroll",
    "Dado biométrico facial é dado pessoal SENSÍVEL (LGPD, Art. 5º, II).": (
        "Facial biometric data is SENSITIVE personal data (Brazil's LGPD, Art. 5, II)."
    ),
    "O QUE é guardado: um vetor numérico (embedding) calculado do seu rosto.": (
        "WHAT is stored: a numeric vector (embedding) computed from your face."
    ),
    "Nenhuma foto é gravada, e o vetor não reconstrói a sua imagem.": (
        "No photo is saved, and the vector cannot rebuild your image."
    ),
    "ONDE: somente neste computador, em um arquivo local com acesso": (
        "WHERE: on this computer only, in a local file readable"
    ),
    "restrito ao seu usuário. Nada é enviado para a internet.": (
        "only by your user. Nothing is sent to the internet."
    ),
    "COMO EXCLUIR: no botão Gerenciar deste modo, a qualquer momento.": (
        "HOW TO DELETE: through this mode's Manage button, at any time."
    ),
    "A exclusão é imediata e definitiva.": "Deletion is immediate and permanent.",
    # --- captura ---
    "Snapshot salvo": "Snapshot saved",
    "Gravando": "Recording",
    "Vídeo salvo": "Video saved",
    "Não consegui gravar o vídeo": "Could not record the video",
}

_language = DEFAULT_LANGUAGE


def set_language(language: str) -> None:
    """Define o idioma da interface. Um idioma desconhecido é recusado."""
    global _language
    if language not in LANGUAGES:
        raise ValueError(f"Idioma '{language}' não suportado. Use: {', '.join(LANGUAGES)}.")
    _language = language


def get_language() -> str:
    return _language


def t(text: str) -> str:
    """Traduz um rótulo. Sem tradução cadastrada, devolve o próprio texto."""
    if _language == DEFAULT_LANGUAGE:
        return text
    return CATALOG.get(text, text)
