# Contador de Dedos

## Sumário
- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
  - [Detecção de Mãos](#detecao-de-maos)
  - [Contagem de Dedos](#contagem-de-dedos)
  - [Visualização em Tempo Real](#visualizacao-em-tempo-real)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Pré-requisitos](#pre-requisitos)
- [Como Configurar e Executar](#como-configurar-e-executar)
- [Arquitetura do Projeto](#arquitetura-do-projeto)
- [Contribuição](#contribuicao)
- [Licença](#licenca)

<br>

## Sobre o Projeto
Este projeto simples em Python utiliza as bibliotecas OpenCV e MediaPipe para detectar e contar o número de dedos levantados em uma mão em tempo real, usando a webcam.

<br>

## Funcionalidades
### Detecção de Mãos: 
Identifica a presença de uma ou duas mãos no quadro da webcam.

### Contagem de Dedos: 
Conta o número de dedos estendidos para cada mão (esquerda e direita) e exibe o total.
O código verifica a posição do topo de cada dedo (pontos 8, 12, 16 e 20) em relação à sua base (pontos 6, 10, 14 e 18, respectivamente). 
Se a ponta do dedo estiver acima da base, ele é considerado levantado. 
O polegar (ponto 4) é tratado de forma diferente, comparando sua posição horizontal.

### Visualização em Tempo Real: 
Desenha os pontos de referência (landmarks) das mãos e exibe os contadores na tela.
Os contadores de dedos para a mão esquerda, direita e o total são exibidos na tela da webcam em tempo real. 
Os pontos de referência das mãos também são desenhados para uma visualização clara.

<br>

## Tecnologias Utilizadas
- Python: Linguagem de programação principal.

- OpenCV: Biblioteca de visão computacional usada para capturar o vídeo da webcam e exibir os resultados.

- MediaPipe: Estrutura de aprendizado de máquina para detecção e rastreamento de mãos.

<br>

## Pré-requisitos
- **Python 3.9 a 3.12** (faixa suportada pelo MediaPipe)
- Uma **webcam**

As dependências (OpenCV + MediaPipe) são instaladas automaticamente pelo `setup.sh`.

<br>

## Como Configurar e Executar

### ⚡ Setup automático (recomendado)

O script [`setup.sh`](./setup.sh) **configura o ambiente com um único comando**: valida o Python, cria um ambiente virtual (`.venv`) e instala as dependências. Ele **não** abre a webcam — só prepara.

```bash
git clone <url-do-repo>
cd ContadorDedos
./setup.sh
```

Acompanhe cada etapa com **barra de progresso e porcentagem**:

```
[3/3] Dependências (OpenCV + MediaPipe)
  ██████████████████████████████ 100%
```

**Opções:** `./setup.sh --reinstall` (atualiza as dependências) · `./setup.sh -h` (ajuda).
O script é **idempotente** — pode rodar de novo com segurança.

Depois de configurar, **execute** o app:

```bash
.venv/bin/python src/main.py
# ou, ativando o ambiente:
source .venv/bin/activate
python src/main.py
```

A janela da sua webcam será aberta e o programa começará a detectar suas mãos e contar os dedos em tempo real. Encerre com **Ctrl+C** no terminal.

> No **macOS**, autorize o acesso à câmera para o seu terminal em **Ajustes > Privacidade e Segurança > Câmera**.

<details>
<summary>🔧 <strong>Setup manual</strong> — sem o <code>setup.sh</code></summary>

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --no-compile -r requirements.txt
python src/main.py
```

> **Por que `--no-compile`?** O wheel do MediaPipe 0.10.35 traz um arquivo de teste com um caractere inválido (`∂`). No Python 3.9 do macOS (locale sem UTF-8), a etapa de compilação de bytecode do pip estoura e aborta toda a instalação. A flag `--no-compile` pula essa etapa — os `.pyc` são gerados sob demanda no import e o app funciona normalmente.

</details>

<br>

## Arquitetura do Projeto
A estrutura do projeto é simples e organizada da seguinte forma:

```
├── .github
│   ├── ISSUE_TEMPLATE/   # templates de bug e sugestão de funcionalidade
│   └── pull_request_template.md
├── src
│   └── main.py           # lógica de detecção e contagem
├── setup.sh              # configura o ambiente (venv + dependências)
├── requirements.txt      # OpenCV + MediaPipe (versões fixadas)
├── Plano_melhoria.md     # roteiro técnico de evolução do projeto
├── CONTRIBUTING.md       # como contribuir
├── README.md
└── LICENSE.md
```

<br>

## Contribuição
Contribuições são bem-vindas! O guia completo — ambiente, padrões de código e fluxo de PR — está no [CONTRIBUTING.md](./CONTRIBUTING.md).

Para reportar um bug ou sugerir uma funcionalidade, abra uma [issue](../../issues/new/choose) usando um dos templates. O roteiro técnico do projeto está no [Plano_melhoria.md](./Plano_melhoria.md).

<br>

## Licença
Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE.md](LICENSE.md) para mais detalhes.

Desenvolvido com 💖