#!/usr/bin/env bash
# Contador de Dedos — setup do ambiente.
# Deixa tudo pronto em um comando: valida o Python, cria o ambiente virtual,
# instala as dependências e as ferramentas de desenvolvimento, baixa TODOS os
# modelos e verifica que o app importa e que a câmera responde.
#
# Uso:
#   ./setup.sh                  # ambiente completo
#   ./setup.sh --web            # inclui o front web (Streamlit, ~200 MB)
#   ./setup.sh --no-dev         # sem pytest/ruff/black/pre-commit
#   ./setup.sh --skip-models    # sem baixar modelos (~130 MB)
#   ./setup.sh --reinstall      # reinstala as dependências
#   ./setup.sh -h               # ajuda
#
# Idempotente: nada é rebaixado ou reinstalado à toa, então pode rodar de novo.

set -eo pipefail

# ------------------------------------------------------------------------------
# Flags
# ------------------------------------------------------------------------------
REINSTALL=false
DEV=true
MODELS=true
WEB=false

for arg in "$@"; do
    case "$arg" in
        --reinstall)   REINSTALL=true ;;
        --no-dev)      DEV=false ;;
        --web)         WEB=true ;;
        --skip-models) MODELS=false ;;
        -h|--help)
            awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "$0"
            exit 0
            ;;
        *)
            echo "Argumento desconhecido: $arg (use -h para ajuda)" >&2
            exit 1
            ;;
    esac
done

# ------------------------------------------------------------------------------
# Plataforma (define o caminho dos binários do venv)
# ------------------------------------------------------------------------------
case "$(uname -s)" in
    Linux*)              PLATFORM="linux" ;;
    Darwin*)             PLATFORM="macos" ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
    *)                   PLATFORM="unknown" ;;
esac

# ------------------------------------------------------------------------------
# Saída colorida
# ------------------------------------------------------------------------------
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; NC=''
fi

print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_error()   { echo -e "${RED}[ERRO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info()    { echo -e "${BLUE}[i]${NC} $1"; }
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# ------------------------------------------------------------------------------
# Progresso (etapa n/total + barra + porcentagem)
# ------------------------------------------------------------------------------
BAR_WIDTH=30
STEP=0
TOTAL_STEPS=5   # Python, venv, dependências, modelos, verificação

draw_bar() { # $1 = porcentagem (0-100)
    local pct="$1" filled i out=""
    filled=$(( pct * BAR_WIDTH / 100 ))
    for ((i = 0; i < BAR_WIDTH; i++)); do
        if ((i < filled)); then out+="█"; else out+="░"; fi
    done
    printf '%s' "$out"
}

progress_header() { # $1 = título da etapa
    STEP=$((STEP + 1))
    local pct
    pct=$(( STEP * 100 / TOTAL_STEPS ))
    (( pct > 100 )) && pct=100
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}[${STEP}/${TOTAL_STEPS}] ${1}${NC}"
    echo -e "  ${GREEN}$(draw_bar "$pct")${NC} ${pct}%"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

trap 'echo; print_error "Setup interrompido (linha $LINENO). Corrija o problema acima e rode novamente."' ERR

# ------------------------------------------------------------------------------
# Raiz do projeto
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "src/contador_dedos/__init__.py" ]; then
    print_error "Rode este script na raiz do projeto Contador de Dedos (src/contador_dedos/ não encontrado)."
    exit 1
fi

print_header "Contador de Dedos — Setup do Ambiente"

# ==============================================================================
# 1. Python (3.9–3.12 — faixa suportada pelo MediaPipe)
# ==============================================================================
progress_header "Python"

# Retorna "MAJOR MINOR" de um interpretador, ou nada se inexistente.
py_ver() { "$1" -c 'import sys; print("%d %d" % sys.version_info[:2])' 2>/dev/null; }

PYTHON=""
for cand in python3.12 python3.11 python3.10 python3.9 python3 python; do
    command -v "$cand" &> /dev/null || continue
    read -r maj min < <(py_ver "$cand") || true
    [ -z "${maj:-}" ] && continue
    if [ "$maj" -eq 3 ] && [ "$min" -ge 9 ] && [ "$min" -le 12 ]; then
        PYTHON="$cand"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    print_error "Nenhum Python compatível encontrado (o MediaPipe requer Python 3.9 a 3.12)."
    print_info "Instale o Python 3.11 (recomendado):"
    if [ "$PLATFORM" = "macos" ]; then
        print_info "  • Homebrew: brew install python@3.11"
    else
        print_info "  • Veja: https://www.python.org/downloads/  (ou o gerenciador da sua distro)"
    fi
    exit 1
fi
print_success "Usando $($PYTHON --version 2>&1) ($PYTHON)"

# ==============================================================================
# 2. Ambiente virtual (.venv)
# ==============================================================================
progress_header "Ambiente virtual (.venv)"

# Binários do venv (Scripts no Windows, bin no restante).
venv_paths() {
    VENV_BIN=".venv/bin"
    [ -d ".venv/Scripts" ] && VENV_BIN=".venv/Scripts"
    VENV_PY="${VENV_BIN}/python"
}
venv_paths

# Um venv guarda caminhos absolutos: renomear ou mover a pasta do projeto o
# quebra, e o erro que aparece depois ("No such file or directory" apontando
# para o caminho antigo) não diz isso. Melhor detectar aqui.
if [ -d ".venv" ] && ! "$VENV_PY" -c 'import sys' &> /dev/null; then
    print_warning "O .venv existente não executa (o projeto foi movido ou renomeado?)."
    print_info "Recriando do zero..."
    rm -rf .venv
fi

if [ -d ".venv" ]; then
    print_success ".venv já existe (reutilizando)"
else
    print_info "Criando o ambiente virtual..."
    "$PYTHON" -m venv .venv
    venv_paths
    print_success ".venv criado"
fi
venv_paths

# ==============================================================================
# 3. Dependências (OpenCV + MediaPipe)
# ==============================================================================
EXTRAS=""
CHECK_IMPORTS='import cv2, mediapipe, onnxruntime'
TITULO="Dependências (OpenCV + MediaPipe + ONNX Runtime)"
if [ "$DEV" = true ]; then
    EXTRAS="dev"
    CHECK_IMPORTS="$CHECK_IMPORTS, pytest, ruff"
    TITULO="Dependências + ferramentas de desenvolvimento"
fi
if [ "$WEB" = true ]; then
    EXTRAS="${EXTRAS:+$EXTRAS,}web"
    CHECK_IMPORTS="$CHECK_IMPORTS, streamlit, streamlit_webrtc"
    TITULO="$TITULO + front web"
fi
progress_header "$TITULO"
PIP_TARGET="."
[ -n "$EXTRAS" ] && PIP_TARGET=".[${EXTRAS}]"

if [ "$REINSTALL" = false ] && "$VENV_PY" -c "$CHECK_IMPORTS" &> /dev/null; then
    print_success "Dependências já instaladas (use --reinstall para atualizar)"
else
    print_info "Instalando dependências (a 1ª vez baixa ~algumas centenas de MB)..."
    "$VENV_PY" -m pip install --upgrade pip &> /dev/null || true
    # --no-compile: o wheel do MediaPipe traz um arquivo de teste com caractere
    # inválido (∂, U+2202). No Python 3.9 do macOS (locale sem UTF-8), a etapa de
    # compilação de bytecode do pip estoura e aborta a instalação inteira. Pular a
    # compilação resolve — o .pyc é gerado sob demanda no import e o app nunca
    # importa esse arquivo de teste.
    if "$VENV_PY" -m pip install --no-compile -e "$PIP_TARGET"; then
        print_success "Dependências instaladas"
    else
        print_error "Falha ao instalar as dependências (veja os erros acima)."
        print_info "Dica: o MediaPipe só tem wheels para Python 3.9–3.12."
        exit 1
    fi
fi

# ==============================================================================
# 4. Modelos de visão
# ==============================================================================
progress_header "Modelos de visão"

# O MediaPipe 0.10.35 removeu a API legada `mp.solutions`; a Tasks API que a
# substituiu precisa dos arquivos de modelo, que não vêm no wheel. Os downloads
# (com verificação de integridade) moram em contador_dedos/vision/, para que as
# URLs e os hashes tenham um único dono — e para que o app também funcione sem
# ter passado por aqui.
if [ "$MODELS" = false ]; then
    print_warning "Pulando os modelos (--skip-models)."
    print_info "O app baixa cada um sob demanda, na primeira vez que o modo abrir."
else
    print_info "Baixando o que faltar (mãos ~7,5 MB · rosto ~0,2 MB · ArcFace ~122 MB)."
    print_info "O pacote do ArcFace é descartado após a extração; ficam ~14 MB."
    if "$VENV_PY" - <<'PYTHON'
from contador_dedos.config import AppConfig
from contador_dedos.vision.embedder import ARCFACE_FILENAME, ensure_arcface_model
from contador_dedos.vision.faces import FACE_MODEL_FILENAME, ensure_face_model
from contador_dedos.vision.hands import ensure_hand_model

config = AppConfig()
alvos = (
    ("detecção de mãos", ensure_hand_model, config.model_path),
    ("detecção de rosto", ensure_face_model, config.models_dir / FACE_MODEL_FILENAME),
    ("ArcFace (reconhecimento facial)", ensure_arcface_model, config.models_dir / ARCFACE_FILENAME),
)
for nome, garantir, caminho in alvos:
    ja_existia = caminho.is_file()
    garantir(caminho)
    print(f"  {'ja tinha  ' if ja_existia else 'baixado   '} {nome}: {caminho.name}")
PYTHON
    then
        print_success "Modelos prontos em models/"
    else
        print_error "Falha ao obter os modelos."
        print_info "Verifique sua conexão e rode o setup de novo, ou use --skip-models"
        print_info "para deixar que o app baixe cada um quando o modo for aberto."
        exit 1
    fi
fi

# ==============================================================================
# 5. Verificação
# ==============================================================================
progress_header "Verificação"

if "$VENV_PY" -c 'import contador_dedos; print(contador_dedos.__version__)' > /dev/null 2>&1; then
    VERSAO="$("$VENV_PY" -c 'import contador_dedos; print(contador_dedos.__version__)')"
    print_success "Pacote importa corretamente (versão ${VERSAO})"
else
    print_error "O pacote não importa. Rode ./setup.sh --reinstall."
    exit 1
fi

# Hooks de qualidade: só fazem sentido com as ferramentas instaladas e em um repo.
if [ "$DEV" = true ] && [ -d ".git" ]; then
    if "$VENV_BIN/pre-commit" install > /dev/null 2>&1; then
        print_success "Hooks de pre-commit instalados"
    else
        print_warning "Não consegui instalar os hooks de pre-commit (siga sem eles)."
    fi
fi

# A câmera é metade do projeto: melhor descobrir agora que a permissão falta do
# que na primeira execução. No macOS, isto dispara o pedido de autorização.
print_info "Testando o acesso à câmera (a luz pode acender por um instante)..."
CAMERA_OK=$("$VENV_PY" - <<'PYTHON' 2>/dev/null || echo "erro"
import cv2

captura = cv2.VideoCapture(0)
aberta = captura.isOpened()
captura.release()
print("sim" if aberta else "nao")
PYTHON
)
if [ "$CAMERA_OK" = "sim" ]; then
    print_success "Câmera acessível"
else
    print_warning "Não consegui abrir a câmera 0."
    if [ "$PLATFORM" = "macos" ]; then
        print_info "No macOS, autorize em Ajustes > Privacidade e Segurança > Câmera —"
        print_info "para o app de onde você vai rodar (Terminal, iTerm ou PyCharm)."
    fi
    print_info "Outra câmera? Use: ${VENV_BIN}/python -m contador_dedos --camera 1"
fi

# ==============================================================================
# Resumo
# ==============================================================================
trap - ERR
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Setup concluído${NC}"
echo -e "  ${GREEN}$(draw_bar 100)${NC} 100%"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Para executar (abre a webcam no menu):"
echo ""
echo -e "  ${GREEN}${VENV_BIN}/python -m contador_dedos${NC}"
echo ""
print_info "Ou pelo comando instalado: ${GREEN}${VENV_BIN}/contador-dedos${NC}"
if [ "$WEB" = true ]; then
    print_info "Front web (só em 127.0.0.1): ${GREEN}${VENV_BIN}/contador-dedos-web${NC}"
fi
print_info "Ative o ambiente com:  ${GREEN}source ${VENV_BIN}/activate${NC}  (depois: ${GREEN}python -m contador_dedos${NC})"
if [ "$DEV" = true ]; then
    echo ""
    print_info "Checagens locais: ${GREEN}${VENV_BIN}/pytest${NC} · ${GREEN}${VENV_BIN}/ruff check .${NC} · ${GREEN}${VENV_BIN}/black --check .${NC}"
fi
echo ""
print_success "Ambiente pronto. Bom trabalho!"
