# Contador de Dedos

[![CI](https://github.com/WallaceCampista/ContadorDedos/actions/workflows/ci.yml/badge.svg?branch=development)](https://github.com/WallaceCampista/ContadorDedos/actions/workflows/ci.yml)
[![Python 3.9–3.12](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/downloads/)
[![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-green)](LICENSE.md)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/lint-ruff-D7FF64)](https://github.com/astral-sh/ruff)

## Sumário
- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
  - [Menu interativo](#menu-interativo)
  - [Detecção de Mãos](#detecao-de-maos)
  - [Reconhecimento de gestos](#reconhecimento-de-gestos)
  - [Números em Libras](#numeros-em-libras)
  - [Contagem de Dedos](#contagem-de-dedos)
  - [Visualização em Tempo Real](#visualizacao-em-tempo-real)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Pré-requisitos](#pre-requisitos)
- [Como Configurar e Executar](#como-configurar-e-executar)
  - [Opções de linha de comando](#opcoes-de-linha-de-comando)
- [Qualidade: testes e lint](#qualidade-testes-e-lint)
- [Arquitetura do Projeto](#arquitetura-do-projeto)
- [Contribuição](#contribuicao)
- [Licença](#licenca)

<br>

## Sobre o Projeto
Este projeto simples em Python utiliza as bibliotecas OpenCV e MediaPipe para detectar e contar o número de dedos levantados em uma mão em tempo real, usando a webcam.

<br>

## Funcionalidades

<h3 id="menu-interativo">Menu interativo</h3>

O app abre em uma **tela inicial** onde você escolhe o que fazer — clicando em um
card ou apertando a tecla que ele mostra. O menu é gerado a partir dos modos
registrados, então cada funcionalidade nova ganha o seu card automaticamente.

```
┌──────────────────────────────────────────────────┐
│                                                  │
│                Contador de Dedos                 │
│             Escolha o que deseja fazer           │
│                                                  │
│  ┌──────────────┐ ┌──────────┐ ┌──────────┐    │
│  │      1       │ │    2     │ │    3     │    │
│  │ Contar Dedos │ │  Gestos  │ │  Libras  │    │
│  └──────────────┘ └──────────┘ └──────────┘    │
│                  ┌──────────┐                   │
│                  │    Q     │                   │
│                  │   Sair   │                   │
│                  └──────────┘                   │
│                                                  │
│     Clique em um card  •  Q encerra    29.9 FPS  │
└──────────────────────────────────────────────────┘
```

**Navegação:**

| Ação | Como |
|------|------|
| Abrir um modo | Clique no card ou aperte o número dele |
| Voltar ao menu | **ESC** ou o botão **← Voltar** no rodapé |
| Encerrar | **Q**, o card **Sair**, ou fechando a janela |

O card sob o mouse fica destacado, e o rodapé mostra sempre os atalhos
disponíveis na tela atual.

### Detecção de Mãos:
Identifica a presença de uma ou duas mãos no quadro da webcam.

<h3 id="reconhecimento-de-gestos">Reconhecimento de gestos</h3>

O modo **Gestos** identifica a configuração de cada mão e mostra o nome dela:

| Gesto | Como fazer |
|-------|-----------|
| **Joinha** | Punho fechado, polegar apontando para cima |
| **Paz** | Indicador e médio levantados, anelar e mínimo recolhidos |
| **OK** | Ponta do polegar encostando na do indicador, os outros três estendidos |
| **Mão aberta** | Os cinco dedos estendidos |
| **Mão fechada** | Punho fechado |

O reconhecimento é **geométrico**: lê as distâncias e posições entre os
landmarks, sem um segundo modelo para baixar. Ele reaproveita o mesmo detector
de mãos do modo de contagem — os dois modos compartilham uma única instância.

Quando a mão não forma nenhum gesto conhecido, a tela mostra `—` em vez de
chutar o mais parecido.

<h3 id="numeros-em-libras">Números em Libras</h3>

O modo **Libras** identifica o numeral pela configuração da mão e mostra o
algarismo com o nome por extenso (`3 · três`).

> **Cobertura: 1 a 5.** Os numerais **0 e 6 a 10 ainda não são reconhecidos**, e
> a própria tela avisa isso. Os motivos são honestos: de 6 a 9 as configurações
> não se reduzem a "N dedos estendidos" e **variam por região**; e o 10, em
> várias variantes, envolve **movimento**, que um reconhecedor de frame único
> não captura. Preferimos não cobrir a chutar a configuração de uma língua real.

O que separa este modo do *Contar Dedos* é **quais** dedos estão estendidos, e
não quantos: três dedos quaisquer somam 3, mas só polegar + indicador + médio é
o numeral **3** em Libras.

| Numeral | Configuração |
|---------|--------------|
| **1** | Indicador |
| **2** | Indicador + médio |
| **3** | Polegar + indicador + médio |
| **4** | Indicador + médio + anelar + mínimo (sem o polegar) |
| **5** | Os cinco dedos |

### Contagem de Dedos:
Conta o número de dedos estendidos para cada mão (esquerda e direita) e exibe o total.
O código verifica a posição da ponta de cada dedo (pontos 8, 12, 16 e 20) em relação à sua articulação PIP (pontos 6, 10, 14 e 18, respectivamente).
Se a ponta estiver acima da articulação, o dedo é considerado levantado.
O polegar (ponto 4) é tratado de forma diferente, comparando sua posição horizontal — por isso depende de saber qual é a mão.

A **lateralidade** vem do classificador do próprio MediaPipe, e não de uma heurística geométrica: o rótulo continua correto mesmo com a mão girada ou de costas.
A contagem também passa por uma **suavização anti-flicker** (o valor mais frequente dos últimos frames), para o número não tremer entre um quadro e outro.

### Visualização em Tempo Real:
Desenha os pontos de referência (landmarks) das mãos e exibe os contadores na tela.
Os contadores de dedos para a mão esquerda, direita e o total são exibidos na tela da webcam em tempo real, junto de um **medidor de FPS** e da dica de atalhos no rodapé.

A imagem é **espelhada** por padrão, como um espelho de verdade: sua mão direita aparece à direita da tela, e cada contador fica do lado em que aquela mão realmente aparece.
Quando não há mão no quadro, a tela diz isso — em vez de mostrar zeros ambíguos.

Os textos ficam sobre **faixas semitransparentes**, têm contorno escuro e escalam
com a resolução da câmera, para permanecerem legíveis em qualquer fundo e em
qualquer webcam.

<br>

## Tecnologias Utilizadas
- Python: Linguagem de programação principal.

- OpenCV: Biblioteca de visão computacional usada para capturar o vídeo da webcam e exibir os resultados.

- MediaPipe (Tasks API): Estrutura de aprendizado de máquina para detecção e rastreamento de mãos, via `HandLandmarker`.

> A partir do MediaPipe 0.10.35 a API legada `mp.solutions` foi removida. O projeto usa a **Tasks API**, que depende do modelo `hand_landmarker.task` (~7,5 MB) — baixado automaticamente pelo `setup.sh` ou na primeira execução, e mantido fora do versionamento.

<br>

## Pré-requisitos
- **Python 3.9 a 3.12** (faixa suportada pelo MediaPipe)
- Uma **webcam**
- **Conexão com a internet** na primeira execução (para baixar o modelo de detecção)

As dependências (OpenCV + MediaPipe) e o modelo de detecção são obtidos automaticamente pelo `setup.sh`.

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
[4/4] Modelo de detecção de mãos
  ██████████████████████████████ 100%
```

**Opções:** `./setup.sh --reinstall` (atualiza as dependências) · `./setup.sh -h` (ajuda).
O script é **idempotente** — pode rodar de novo com segurança.

Depois de configurar, **execute** o app:

```bash
.venv/bin/python -m contador_dedos
# ou, ativando o ambiente:
source .venv/bin/activate
python -m contador_dedos
```

A janela da sua webcam abre no **menu**; clique em *Contar Dedos* (ou aperte `1`)
ou em *Gestos* (`2`) ou *Libras* (`3`) para começar. **ESC** volta ao menu e
**Q** encerra.

> Se o modelo `hand_landmarker.task` ainda não estiver em `models/`, ele é baixado automaticamente nesta primeira execução.

> No **macOS**, autorize o acesso à câmera para o seu terminal em **Ajustes > Privacidade e Segurança > Câmera**.

<h3 id="opcoes-de-linha-de-comando">Opções de linha de comando</h3>

Todos os parâmetros têm um padrão sensato — rodar sem argumentos funciona. Use `--help` para ver a lista completa.

| Opção | Padrão | O que faz |
|-------|--------|-----------|
| `--camera N` | `0` | Índice da câmera a usar. |
| `--max-hands N` | `2` | Número máximo de mãos detectadas ao mesmo tempo. |
| `--detection-confidence F` | `0.5` | Confiança mínima para considerar uma detecção válida (0 a 1). |
| `--tracking-confidence F` | `0.5` | Confiança mínima para manter o rastreamento entre frames (0 a 1). |
| `--smooth-window N` | `5` | Frames usados na suavização anti-flicker da contagem. |
| `--mirror` / `--no-mirror` | `--mirror` | Espelha (ou não) a imagem da câmera. |
| `--model ARQUIVO` | `models/hand_landmarker.task` | Caminho do modelo; baixado se estiver faltando. |

```bash
# Segunda câmera, uma mão só e sem espelhamento
.venv/bin/python -m contador_dedos --camera 1 --max-hands 1 --no-mirror
```

> O `setup.sh` instala o projeto em modo editável, então o comando
> **`.venv/bin/contador-dedos`** também funciona — com as mesmas opções.

<br>

## Qualidade: testes e lint

O projeto é verificado por **Ruff** (lint + ordenação de imports), **Black**
(formatação) e **pytest**. A suíte cobre a lógica pura — contagem, lateralidade,
suavização, CLI, desenho e integridade do download do modelo — e por isso roda
**sem webcam, sem modelo e sem rede**.

```bash
pip install -e ".[dev]"   # ferramentas de desenvolvimento

pytest                    # testes
ruff check .              # lint
black --check .           # formatação
```

Para rodar tudo automaticamente a cada commit:

```bash
pre-commit install
pre-commit run --all-files   # ou de uma vez, em tudo
```

A [CI](.github/workflows/ci.yml) repete esses três checks em uma matriz de
**Python 3.9 a 3.12** a cada push e pull request.

<details>
<summary>🔧 <strong>Setup manual</strong> — sem o <code>setup.sh</code></summary>

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --no-compile -r requirements.txt
python -m contador_dedos
```

> **Por que `--no-compile`?** O wheel do MediaPipe 0.10.35 traz um arquivo de teste com um caractere inválido (`∂`). No Python 3.9 do macOS (locale sem UTF-8), a etapa de compilação de bytecode do pip estoura e aborta toda a instalação. A flag `--no-compile` pula essa etapa — os `.pyc` são gerados sob demanda no import e o app funciona normalmente.

</details>

<br>

## Arquitetura do Projeto
O código é organizado em **camadas**, para que cada funcionalidade nova entre
como um módulo plugável em vez de engordar um script único:

- **`core/`** — infraestrutura: a câmera como *context manager*, o relógio do
  vídeo e a anotação do frame.
- **`ui/`** — o tema (paleta e métricas), as primitivas de desenho (cards,
  painéis, botões) e o menu. Trocar a HighGUI por PySide6 mexeria só aqui.
- **`vision/`** — a única camada que conhece o MediaPipe, mais a leitura
  geométrica da mão (`handshape.py`) que contagem e gestos compartilham.
- **`modes/`** — cada feature é um `Mode` (contagem, gestos e Libras hoje;
  rosto adiante). Adicionar uma = criar a classe e registrá-la. Todos
  compartilham **um único** detector de mãos, criado uma vez.
- **`app.py`** — o loop, que conhece apenas o contrato `Mode`.

A estrutura de arquivos:

```
├── .github
│   ├── ISSUE_TEMPLATE/   # templates de bug e sugestão de funcionalidade
│   ├── workflows/ci.yml  # lint + testes em Python 3.9–3.12
│   └── pull_request_template.md
├── models/               # hand_landmarker.task (baixado, fora do versionamento)
├── src/contador_dedos/
│   ├── __main__.py       # python -m contador_dedos
│   ├── app.py            # loop principal e roteamento entre telas
│   ├── config.py         # AppConfig (dataclass) + CLI
│   ├── core/             # câmera, relógio do vídeo e anotação do frame
│   ├── ui/               # tema, primitivas de desenho e a tela de menu
│   ├── vision/           # tudo que fala com o MediaPipe (+ download do modelo)
│   └── modes/            # features plugáveis: base.py (ABC) + um arquivo por modo
├── tests/                # suíte pytest (sem webcam, sem modelo, sem rede)
├── pyproject.toml        # metadados, dependências, entry point e config das ferramentas
├── .pre-commit-config.yaml
├── setup.sh              # configura o ambiente (venv + dependências + modelo)
├── requirements.txt      # aponta para o pyproject.toml
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
