#!/usr/bin/env bash
# Contador de Dedos — setup do ambiente de desenvolvimento.
# Prepara tudo para rodar o app: valida o Python, cria um ambiente virtual
# (.venv) e instala as dependências (OpenCV + MediaPipe). NÃO abre a webcam —
# a execução fica por sua conta (ver o resumo ao final).
#
# Uso:
#   ./setup.sh                 # configura o ambiente
#   ./setup.sh --reinstall     # recria/atualiza as dependências
#   ./setup.sh -h              # ajuda
#
# Idempotente: pode ser executado várias vezes com segurança.

set -eo pipefail

# ------------------------------------------------------------------------------
# Flags
# ------------------------------------------------------------------------------
REINSTALL=false

for arg in "$@"; do
    case "$arg" in
        --reinstall)  REINSTALL=true ;;
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
TOTAL_STEPS=3   # Python, ambiente virtual, dependências

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

if [ ! -f "src/main.py" ]; then
    print_error "Rode este script na raiz do projeto Contador de Dedos (src/main.py não encontrado)."
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

if [ -d ".venv" ]; then
    print_success ".venv já existe (reutilizando)"
else
    print_info "Criando o ambiente virtual..."
    "$PYTHON" -m venv .venv
    print_success ".venv criado"
fi

# Binários do venv (Scripts no Windows, bin no restante).
VENV_BIN=".venv/bin"
[ -d ".venv/Scripts" ] && VENV_BIN=".venv/Scripts"
VENV_PY="${VENV_BIN}/python"

# ==============================================================================
# 3. Dependências (OpenCV + MediaPipe)
# ==============================================================================
progress_header "Dependências (OpenCV + MediaPipe)"

if [ "$REINSTALL" = false ] && "$VENV_PY" -c 'import cv2, mediapipe' &> /dev/null; then
    print_success "Dependências já instaladas (use --reinstall para atualizar)"
else
    print_info "Instalando dependências (a 1ª vez baixa ~algumas centenas de MB)..."
    "$VENV_PY" -m pip install --upgrade pip &> /dev/null || true
    # --no-compile: o wheel do MediaPipe traz um arquivo de teste com caractere
    # inválido (∂, U+2202). No Python 3.9 do macOS (locale sem UTF-8), a etapa de
    # compilação de bytecode do pip estoura e aborta a instalação inteira. Pular a
    # compilação resolve — o .pyc é gerado sob demanda no import e o app nunca
    # importa esse arquivo de teste.
    if "$VENV_PY" -m pip install --no-compile -r requirements.txt; then
        print_success "Dependências instaladas"
    else
        print_error "Falha ao instalar as dependências (veja os erros acima)."
        print_info "Dica: o MediaPipe só tem wheels para Python 3.9–3.12."
        exit 1
    fi
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

echo "Para executar (abre a webcam):"
echo ""
echo -e "  ${GREEN}${VENV_BIN}/python src/main.py${NC}"
echo ""
print_info "Ative o ambiente com:  ${GREEN}source ${VENV_BIN}/activate${NC}  (depois: ${GREEN}python src/main.py${NC})"
if [ "$PLATFORM" = "macos" ]; then
    print_info "No macOS, autorize a câmera para o seu terminal em Ajustes > Privacidade e Segurança > Câmera."
fi
echo ""
print_success "Ambiente pronto. Bom trabalho!"
