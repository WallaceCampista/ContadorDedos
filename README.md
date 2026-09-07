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
  - [Identificação por rosto](#identificacao-por-rosto)
  - [Snapshots e gravação](#snapshots-e-gravacao)
  - [Idioma e som](#idioma-e-som)
  - [Contagem de Dedos](#contagem-de-dedos)
  - [Visualização em Tempo Real](#visualizacao-em-tempo-real)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Pré-requisitos](#pre-requisitos)
- [Como Configurar e Executar](#como-configurar-e-executar)
  - [Opções de linha de comando](#opcoes-de-linha-de-comando)
- [Versão web](#versao-web)
- [Privacidade e LGPD](#privacidade-e-lgpd)
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
│       ┌──────────────┐ ┌──────────┐             │
│       │      4       │ │    Q     │             │
│       │  Rosto (ID)  │ │   Sair   │             │
│       └──────────────┘ └──────────┘             │
│                                                  │
│     Clique em um card  •  Q encerra    29.9 FPS  │
└──────────────────────────────────────────────────┘
```

**Navegação:**

| Ação | Como |
|------|------|
| Abrir um modo | Clique no card ou aperte o número dele |
| Voltar ao menu | **ESC** ou o botão **← Voltar** no rodapé |
| Salvar um snapshot | **S** |
| Gravar vídeo | **R** (aperte de novo para parar) |
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

<h3 id="identificacao-por-rosto">Identificação por rosto</h3>

O modo **Rosto (ID)** detecta rostos, compara com uma base **local** de pessoas
cadastradas e mostra o nome de quem reconheceu — ou `Desconhecido`.

O cadastro passa obrigatoriamente por uma **tela de consentimento** que explica
o que é guardado, onde e como excluir. Depois vêm o nome e a captura de 12
quadros, cuja média vira o vetor salvo. O botão **Gerenciar** lista quem está
cadastrado e permite **excluir** a qualquer momento.

> **Modelos.** O detector de rosto (224 KB) e o ArcFace (~122 MB de download,
> ~14 MB em disco depois da extração) já vêm no `setup.sh`. Se você pulou com
> `--skip-models`, eles são baixados na primeira vez que este modo abrir — e aí
> a janela fica parada durante o download.

Se o reconhecimento errar, ajuste `--face-threshold`: **menor = mais rigor**
(mais `Desconhecido`, menos confusão entre pessoas parecidas).

### Contagem de Dedos:
Conta o número de dedos estendidos para cada mão (esquerda e direita) e exibe o total.

Os **quatro dedos longos** usam a ponta (pontos 8, 12, 16 e 20) contra a própria
articulação PIP (pontos 6, 10, 14 e 18): ponta acima da articulação significa
dedo levantado.

O **polegar** precisa de outra régua, porque ele se abre para o lado em vez de
para cima. A conta compara a distância da **ponta** e da **base** do polegar até
a base do dedo mínimo — o ponto da palma mais afastado dele. Recolher o polegar
leva a ponta na direção do mínimo e encurta essa distância; abrir, alonga.

> Medir da base à ponta importa: a versão anterior comparava a ponta com a
> articulação vizinha, e nessa distância curta um polegar levantado *junto* dos
> dedos (em vez de aberto de lado) deixava só uns 5 px de diferença — ruído
> suficiente para a mão aberta contar 4. Da base à ponta o segmento é umas três
> vezes maior.

A **lateralidade** vem do classificador do MediaPipe e serve para escolher em
qual painel a contagem entra; **a contagem em si não depende dela**. Uma sutileza
que vale registrar: o rótulo descreve a mão *como ela aparece na imagem*, então
com o espelho ligado a sua mão direita aparece como uma esquerda — o app faz essa
conversão antes de exibir.

A contagem também passa por uma **suavização anti-flicker** (o valor mais
frequente dos últimos frames), para o número não tremer entre um quadro e outro.

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

- ONNX Runtime: Executa o modelo ArcFace do reconhecimento facial.

- sounddevice: Toca o feedback sonoro opcional (`--sound`).

- Streamlit + streamlit-webrtc: Front web opcional, com vídeo em tempo real.

- MediaPipe (Tasks API): Estrutura de aprendizado de máquina para detecção e rastreamento de mãos, via `HandLandmarker`.

> A partir do MediaPipe 0.10.35 a API legada `mp.solutions` foi removida. O projeto usa a **Tasks API**, que depende de arquivos de modelo que não vêm no wheel — baixados pelo `setup.sh` (ou sob demanda), verificados por SHA-256 e mantidos fora do versionamento.

<br>

## Pré-requisitos
- **Python 3.9 a 3.12** (faixa suportada pelo MediaPipe)
- Uma **webcam**
- **Conexão com a internet** na primeira execução (para baixar o modelo de detecção)

As dependências, as ferramentas de desenvolvimento e todos os modelos são obtidos automaticamente pelo `setup.sh`.

<br>

## Como Configurar e Executar

### ⚡ Setup automático (recomendado)

O script [`setup.sh`](./setup.sh) **deixa tudo pronto em um comando**: valida o Python, cria o ambiente virtual (`.venv`), instala as dependências e as ferramentas de desenvolvimento, baixa **todos os modelos** e verifica que o app importa e que a câmera responde.

```bash
git clone <url-do-repo>
cd ContadorDedos
./setup.sh
```

Acompanhe cada etapa com **barra de progresso e porcentagem**:

```
[5/5] Verificação
  ██████████████████████████████ 100%
```

**Opções:**

| Flag | O que muda |
|------|-----------|
| `--no-dev` | Não instala pytest/ruff/black/pre-commit. |
| `--web` | Instala também o front web (Streamlit, ~200 MB). |
| `--skip-models` | Não baixa os modelos (~130 MB); o app os busca sob demanda. |
| `--reinstall` | Reinstala as dependências. |
| `-h` | Ajuda. |

O script é **idempotente**: nada é rebaixado ou reinstalado à toa, então pode
rodar de novo com segurança. Ele também detecta um `.venv` quebrado — o que
acontece se a pasta do projeto for movida ou renomeada — e o recria.

Depois de configurar, **execute** o app:

```bash
.venv/bin/python -m contador_dedos
# ou, ativando o ambiente:
source .venv/bin/activate
python -m contador_dedos
```

A janela da sua webcam abre no **menu**; clique em *Contar Dedos* (ou aperte `1`)
ou em *Gestos* (`2`), *Libras* (`3`) ou *Rosto (ID)* (`4`) para começar.
**ESC** volta ao menu e **Q** encerra.

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
| `--model ARQUIVO` | `models/hand_landmarker.task` | Caminho do modelo de mãos; baixado se estiver faltando. |
| `--faces-db ARQUIVO` | `faces/faces.npz` | Base local de rostos cadastrados. |
| `--face-threshold F` | `0.62` | Distância máxima para reconhecer um rosto; menor = mais rigor. |
| `--output-dir PASTA` | `capturas/` | Onde salvar snapshots e gravações. |
| `--lang pt\|en` | `pt` | Idioma da interface. |
| `--sound` / `--no-sound` | `--no-sound` | Bipe ao mudar a contagem ou reconhecer alguém. |

```bash
# Segunda câmera, uma mão só e sem espelhamento
.venv/bin/python -m contador_dedos --camera 1 --max-hands 1 --no-mirror
```

> O `setup.sh` instala o projeto em modo editável, então o comando
> **`.venv/bin/contador-dedos`** também funciona — com as mesmas opções.

<br>

<h3 id="snapshots-e-gravacao">Snapshots e gravação</h3>

Em qualquer tela, **S** salva um PNG e **R** liga/desliga a gravação em MP4. Os
arquivos vão para `capturas/`, nomeados com data e hora — nada é sobrescrito.

O que é salvo é **o que você vê**: landmarks, contadores e rodapé incluídos. A
única exceção é o indicador `● Gravando`, desenhado depois de o frame ir para o
arquivo — assim o vídeo sai limpo.

```bash
.venv/bin/python -m contador_dedos --output-dir ~/Desktop/capturas
```

<h3 id="idioma-e-som">Idioma e som</h3>

A interface fala **português** e **inglês**:

```bash
.venv/bin/python -m contador_dedos --lang en
```

O nome do app permanece "Contador de Dedos" nos dois idiomas — é o nome do
projeto, não um rótulo.

O **feedback sonoro** (um bipe curto ao mudar a contagem ou reconhecer alguém)
vem **desligado**; ligue com `--sound`. Em máquinas sem saída de áudio ele
simplesmente não toca, sem atrapalhar o resto.

<br>

<h2 id="versao-web">Versão web</h2>

Além da janela nativa, o projeto roda no navegador — **os mesmos modos, a mesma
lógica**, trocando só a moldura: a barra lateral substitui os cards e o vídeo
chega por WebRTC.

```bash
./setup.sh --web                  # instala o extra (Streamlit, ~200 MB)
.venv/bin/contador-dedos-web      # abre em http://127.0.0.1:8501
```

O front web tem **contagem, gestos e Libras** completos. No modo **Rosto** ele
**reconhece e exclui**, mas **não cadastra**: o cadastro exige a tela de
consentimento, que vive no app nativo. Manter uma única implementação do
consentimento é mais seguro do que ter duas para errar.

> **Só no laço local.** O servidor sobe fixado em `127.0.0.1`. Isso é
> deliberado: a base de rostos é dado biométrico, e expor a página na rede
> mudaria o perfil de risco do projeto inteiro.

Uma limitação conhecida no macOS: `PyAV` e `opencv-python` embarcam versões
diferentes do `libavdevice`, e o sistema imprime um aviso sobre classes
duplicadas ao iniciar. Não observamos falha por causa disso, mas fica o registro.

<br>

## Privacidade e LGPD

Dados biométricos faciais são **dados pessoais sensíveis** (LGPD, Art. 5º, II).
O modo de rosto foi construído com essas garantias, e elas não são opcionais:

| Garantia | Como é cumprida |
|---|---|
| **Consentimento explícito** | O cadastro só começa depois de uma tela que explica o quê, o onde e o como excluir — sem atalho para pulá-la. |
| **Somente local** | A base fica em `faces/faces.npz` na sua máquina. Não há nenhuma chamada de rede na camada de armazenamento. |
| **Minimização** | Guardamos **embeddings** (vetores numéricos), nunca as fotos. O vetor serve para comparar, mas não reconstrói a sua imagem. |
| **Acesso restrito** | Os arquivos são gravados com permissão `0600` — só o seu usuário lê. |
| **Direito ao esquecimento** | Botão **Excluir** por pessoa, em *Gerenciar*. A remoção é imediata e persiste em disco. |
| **Fora do versionamento** | `faces/`, `*.npz`, `*.onnx` e `*.tflite` estão no `.gitignore`. Nenhum dado biométrico entra no repositório. |
| **Sem exposição em rede** | O front web sobe fixado em `127.0.0.1`, e não faz cadastro — só reconhecimento e exclusão. |

Um índice legível em `faces/faces.json` lista **quem** está cadastrado (sem
expor vetor nenhum), para você auditar o conteúdo da base a qualquer momento.
Para apagar tudo de uma vez, basta remover a pasta `faces/`.

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
  vídeo, a anotação do frame, a captura (`recorder.py`) e o som (`audio.py`).
- **`ui/`** — o tema (paleta e métricas), as primitivas de desenho (cards,
  painéis, botões) e o menu. Trocar a HighGUI por PySide6 mexeria só aqui.
- **`vision/`** — a única camada que conhece o MediaPipe e o ArcFace, mais a
  leitura geométrica da mão (`handshape.py`) que contagem, gestos e Libras
  compartilham.
- **`storage/`** — a base local de rostos. Nenhuma chamada de rede aqui, por
  construção.
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
│   ├── i18n.py           # catálogo pt/en dos rótulos
│   ├── core/             # câmera, relógio, anotação, captura e som
│   ├── ui/               # tema, primitivas de desenho e a tela de menu
│   ├── web/              # front Streamlit (extra opcional `[web]`)
│   ├── vision/           # MediaPipe, ArcFace e o download dos modelos
│   ├── storage/          # base local de rostos (nunca versionada)
│   └── modes/            # features plugáveis: base.py (ABC) + um arquivo por modo
├── tests/                # suíte pytest (sem webcam, sem modelo, sem rede)
├── pyproject.toml        # metadados, dependências, entry point e config das ferramentas
├── .pre-commit-config.yaml
├── setup.sh              # configura o ambiente inteiro (venv + deps + modelos)
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
