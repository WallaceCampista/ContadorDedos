"""Página Streamlit do Contador de Dedos.

Roda o mesmo pipeline do app nativo sobre o vídeo que chega por WebRTC. Os modos
são os mesmos objetos `Mode`; o que muda é a moldura — a barra lateral substitui
os cards, e o vídeo vai para o navegador em vez de uma janela do OpenCV.
"""

from __future__ import annotations

import av
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

# Imports absolutos de propósito: o Streamlit executa este arquivo como um
# script solto, fora do pacote, e imports relativos falhariam.
from contador_dedos.config import AppConfig, parse_args
from contador_dedos.i18n import set_language, t
from contador_dedos.modes.face_id import CONSENT_LINES
from contador_dedos.vision.model import ModelError
from contador_dedos.web.engine import FACE_MODE_NAME, FaceEngine, HandEngine

TITLE = "Contador de Dedos"
#: Configuração de ICE. Só servidor público de STUN; nada de mídia sai daqui.
RTC_CONFIG = {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
#: Argumentos comuns aos dois streamers.
STREAM_KWARGS = {
    "mode": WebRtcMode.SENDRECV,
    "frontend_rtc_configuration": RTC_CONFIG,
    "server_rtc_configuration": RTC_CONFIG,
    "media_stream_constraints": {"video": True, "audio": False},
}


@st.cache_resource(show_spinner="Carregando o detector de mãos…")
def _hand_engine() -> HandEngine:
    return HandEngine(parse_args([]))


@st.cache_resource(show_spinner="Carregando o reconhecimento facial…")
def _face_engine() -> FaceEngine:
    return FaceEngine(parse_args([]))


# ---------------------------------------------------------------------------
# Telas
# ---------------------------------------------------------------------------


def hand_view(mode_name: str, mirrored: bool) -> None:
    engine = _hand_engine()

    def callback(frame: av.VideoFrame) -> av.VideoFrame:
        image = engine.process(frame.to_ndarray(format="bgr24"), mode_name, mirrored)
        return av.VideoFrame.from_ndarray(image, format="bgr24")

    webrtc_streamer(key=f"mao-{mode_name}", video_frame_callback=callback, **STREAM_KWARGS)


def face_view(mirrored: bool, threshold: float) -> None:
    try:
        engine = _face_engine()
    except (ModelError, OSError) as error:
        st.error(f"Reconhecimento facial indisponível: {error}")
        st.caption(
            "Rode `./setup.sh` para baixar os modelos, ou abra o modo Rosto no "
            "app nativo uma vez."
        )
        return

    db = engine.db()
    cadastrados = db.names()

    def callback(frame: av.VideoFrame) -> av.VideoFrame:
        image = engine.process(frame.to_ndarray(format="bgr24"), db, threshold, mirrored)
        return av.VideoFrame.from_ndarray(image, format="bgr24")

    webrtc_streamer(key="rosto", video_frame_callback=callback, **STREAM_KWARGS)

    st.subheader("Rostos cadastrados")
    if not cadastrados:
        st.info(
            "Nenhum rosto cadastrado. O **cadastro é feito no app nativo** "
            "(`python -m contador_dedos`, modo Rosto), onde fica a tela de "
            "consentimento exigida pela LGPD."
        )
        return

    for nome in cadastrados:
        coluna_nome, coluna_botao = st.columns([4, 1])
        coluna_nome.write(nome)
        if coluna_botao.button("Excluir", key=f"del-{nome}", type="secondary"):
            db.delete(nome)
            st.rerun()

    with st.expander("O que está guardado sobre essas pessoas"):
        for linha in CONSENT_LINES:
            if linha:
                st.write(t(linha))


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title=TITLE, page_icon="✋", layout="centered")
    config = AppConfig()

    with st.sidebar:
        st.title(TITLE)
        idioma = st.radio("Idioma / Language", ("pt", "en"), horizontal=True)
        set_language(idioma)

        opcoes = [*_hand_engine().mode_names(), FACE_MODE_NAME]
        escolhido = st.radio(t("Escolha o que deseja fazer"), opcoes)
        espelhar = st.toggle("Espelhar a imagem", value=True)
        limiar = st.slider(
            "Rigor do reconhecimento facial",
            0.20,
            1.20,
            config.face_threshold,
            0.02,
            help="Distância máxima para reconhecer alguém. Menor = mais rigor.",
            disabled=escolhido != FACE_MODE_NAME,
        )
        st.caption("Tudo roda nesta máquina. Nenhum vídeo sai daqui.")

    st.header(t(escolhido))
    if escolhido == FACE_MODE_NAME:
        face_view(espelhar, limiar)
    else:
        hand_view(escolhido, espelhar)


main()
