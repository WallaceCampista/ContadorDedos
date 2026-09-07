# Plano de Melhoria — Contador de Dedos

> Documento de planejamento técnico. Descreve o estado atual do projeto, os
> problemas identificados e um roteiro priorizado de evolução para
> **potencializar** o projeto — de script pessoal a uma aplicação **modular,
> testável e extensível**, com uma **interface interativa** onde o usuário
> escolhe o que fazer, e preparada para uma futura **identificação por face**.

**Data:** 2026-07-05
**Escopo analisado:** `src/main.py`, `setup.sh`, `requirements.txt`, `README.md`, `.gitignore`, estrutura do repositório.

### Índice
1. [Diagnóstico do estado atual](#1-diagnóstico-do-estado-atual)
2. [Problemas identificados (por prioridade)](#2-problemas-identificados-por-prioridade)
3. [Arquitetura-alvo](#3-arquitetura-alvo)
4. [Interface interativa (UI/UX)](#4-interface-interativa-uiux)
5. [Nova funcionalidade: Identificação por Face](#5-nova-funcionalidade-identificação-por-face)
6. [Roteiro de evolução (faseado)](#6-roteiro-de-evolução-faseado)
7. [Backlog priorizado](#7-backlog-priorizado)
8. [Próximos passos imediatos](#8-próximos-passos-imediatos)

---

## 1. Diagnóstico do estado atual

O projeto é funcional e cumpre seu propósito: detecta mãos via MediaPipe e conta
dedos levantados em tempo real. A documentação (`README.md`) e o `setup.sh` já
estão acima da média para um projeto pessoal — bem escritos, idempotentes e com
boa UX de instalação.

O ponto fraco está **concentrado no código-fonte**: todo o `main.py` roda em
escopo global, sem funções, sem tratamento de erros, sem finalização de recursos
e sem forma limpa de encerrar. Isso limita a manutenção, impede testes e trava a
adição de novas funcionalidades — exatamente o que precisamos destravar para
suportar um **menu interativo** e a **identificação por face**.

### Pontos fortes
- Ideia clara e resultado visual imediato.
- `setup.sh` robusto (detecção de Python 3.9–3.12, venv, barra de progresso, idempotência).
- README completo, em português, com sumário e instruções de execução.
- `.gitignore` adequado para Python.

### Fraquezas estruturais
- Lógica monolítica em escopo global — impossível de reutilizar ou testar.
- Sem tratamento de falhas (câmera ausente, frame vazio).
- Recursos nunca liberados; encerramento apenas via `Ctrl+C`.
- Uma única funcionalidade fixa — não há como o usuário **escolher** o que fazer.
- Dependências sem versão fixada (build não reproduzível).
- Sem testes, sem lint/format, sem CI.
- Artefatos da IDE (`.idea/`) versionados no repositório.

---

## 2. Problemas identificados (por prioridade)

### 🔴 P0 — Bugs e correção (resolver primeiro)

| # | Problema | Onde | Impacto |
|---|----------|------|---------|
| 1 | **Sem verificação de frame válido.** `video.read()` pode retornar `check=False` e `img=None`; a linha seguinte (`img.shape`) quebra com `AttributeError`. | `main.py:11-15` | Crash quando a câmera desconecta ou não abre. |
| 2 | **Câmera nunca é validada.** Não há `video.isOpened()`; se a câmera falhar, o loop entra em erro sem mensagem clara. | `main.py:4` | Falha silenciosa/confusa. |
| 3 | **Recursos nunca liberados.** Faltam `video.release()` e `cv2.destroyAllWindows()`. | fim do loop | Câmera fica "presa"; janela órfã. |
| 4 | **Sem tecla de saída.** `cv2.waitKey(1)` não checa retorno; encerrar só com `Ctrl+C` (o README admite isso). | `main.py:63` | UX ruim; fecha de forma abrupta. |
| 5 | **Rótulo trocado com o valor.** O rótulo `"Direita"` é desenhado sobre o valor `contador_esquerda`, e vice-versa. | `main.py:52-56` | Exibe o número da mão errada sob cada rótulo. |
| 6 | **Imagem não espelhada.** Sem `cv2.flip`, a webcam não funciona como espelho — a mão direita da pessoa aparece à esquerda da tela, invertendo a intuição de "esquerda/direita". | `main.py:11-12` | Confusão de lateralidade. |
| 7 | **Handedness por heurística frágil.** A lateralidade é inferida por geometria (`pontos[17][0] < pontos[5][0]`) em vez de usar `results.multi_handedness` do MediaPipe. | `main.py:31` | Erra quando a mão está girada/de costas. |

### 🟠 P1 — Qualidade de código

- **Escopo global, sem funções.** Nada de `main()` nem `if __name__ == "__main__":`. Impede import, reuso e teste.
- **Números mágicos** espalhados: índices de landmarks (`4, 3, 8, 12, 16, 20`), limiares, coordenadas de texto. Sem nomes que expliquem a intenção.
- **Sem type hints nem docstrings.**
- **Nomenclatura confusa:** `hand` vs. `Hand`, mistura de português/inglês (`contador`, `points`, `dedos`).
- **Configuração hardcoded:** índice da câmera (`0`), `max_num_hands=2`, confianças de detecção não são ajustáveis.
- **Sem contador de FPS** nem métricas de desempenho.
- **Contagem "treme"** entre frames (sem suavização/debounce), gerando flicker no número exibido.

### 🟡 P2 — Infraestrutura e repositório

- **`requirements.txt` sem versões fixadas** (`opencv-python`, `mediapipe`). Build não reproduzível.
- **Sem testes automatizados.**
- **Sem linter/formatter** (ruff, black) nem `pyproject.toml`.
- **Sem CI** (GitHub Actions) para lint/testes em cada push/PR.
- **`.idea/` versionado.** Está no `.gitignore`, mas os arquivos já estavam rastreados antes — precisam ser removidos do índice com `git rm --cached`.
- **Sem `pyproject.toml`/empacotamento** — não dá para instalar como pacote nem definir entry point.
- **Sem `CONTRIBUTING.md`** nem templates de issue/PR.

---

## 3. Arquitetura-alvo

A refatoração persegue um objetivo central: **transformar "um script que faz uma
coisa" em "uma plataforma que hospeda vários modos"**. Isso é o que torna
possível o menu clicável e o encaixe limpo da identificação por face, sem
reescrever tudo a cada nova ideia.

### 3.1 Princípios
- **Separação de responsabilidades:** captura (I/O) ≠ visão (detecção) ≠ lógica ≠ UI ≠ persistência.
- **Lógica pura e testável:** a regra de negócio (contar dedos, comparar faces) não depende de OpenCV/câmera e pode ser testada com dados sintéticos.
- **Modos plugáveis (Strategy/Plugin):** cada funcionalidade é um `Mode` autocontido. Adicionar um modo = criar uma classe e registrá-la — o menu se atualiza sozinho.
- **Recursos com ciclo de vida garantido:** câmera e modelos são _context managers_ (resolvem os P0 de cleanup).
- **Configuração injetada:** um objeto de config (dataclass) substitui os valores hardcoded, carregável de arquivo/CLI/env.

### 3.2 Estrutura de pacote proposta

```
src/contador_dedos/
├── __init__.py
├── __main__.py            # ponto de entrada → abre o menu (python -m contador_dedos)
├── app.py                 # orquestrador: loop principal + roteamento de telas
├── config.py              # dataclass de configuração (câmera, confiança, tema…)
├── core/
│   ├── camera.py          # captura como context manager (validação + reconexão)
│   ├── pipeline.py        # estágios: captura → detecção → anotação → render
│   └── overlay.py         # helpers de desenho (texto, FPS, caixas, landmarks)
├── vision/
│   ├── hands.py           # wrapper do MediaPipe Hands
│   ├── faces.py           # wrapper de detecção + embedding de face
│   └── landmarks.py       # constantes de landmarks (fim dos números mágicos)
├── modes/                 # cada "modo" = uma feature plugável (Strategy)
│   ├── base.py            # interface Mode (ABC)
│   ├── finger_counter.py  # contagem de dedos (a lógica atual, limpa)
│   ├── gesture.py         # reconhecimento de gestos (futuro)
│   └── face_id.py         # identificação por face (futuro)
├── ui/
│   ├── menu.py            # tela inicial com cards clicáveis
│   ├── widgets.py         # botões/cards + hit-testing de clique
│   └── theme.py           # paleta, fontes, espaçamentos
└── storage/
    ├── faces_db.py        # persistência local de embeddings (cadastro de rostos)
    └── models/            # modelos baixados (gitignored)
```

### 3.3 Contrato de um Modo (Strategy plugável)

```python
# modes/base.py
from abc import ABC, abstractmethod
import numpy as np

class Mode(ABC):
    """Uma funcionalidade selecionável no menu."""
    name: str          # rótulo exibido no card
    icon: str          # emoji/ícone do card

    @abstractmethod
    def process(self, frame: np.ndarray) -> np.ndarray:
        """Recebe um frame BGR e devolve o frame anotado."""

    def on_mouse(self, event: int, x: int, y: int) -> None:
        """Cliques específicos do modo (opcional)."""

    def close(self) -> None:
        """Libera recursos do modo (opcional)."""
```

O `app.py` mantém um **registro** de modos; o menu é gerado a partir dele
(_data-driven_): adicionar `FaceId()` à lista faz um novo card aparecer
automaticamente.

```python
# app.py (esboço)
MODES: list[Mode] = [FingerCounter(), GestureRecognizer(), FaceId(db)]

class App:
    def run(self) -> None:
        with Camera(self.cfg.camera) as cam:      # cleanup garantido (P0 #1-3)
            while self.running:
                frame = cam.read_mirrored()        # flip = efeito espelho (P0 #6)
                frame = self.screen.process(frame)  # menu OU modo atual
                cv2.imshow(WINDOW, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"),): self.running = False   # sair (P0 #4)
                if key == 27: self.go_home()                  # ESC volta ao menu
```

### 3.4 Diagrama de fluxo

```
                    ┌──────────────┐
                    │   Câmera     │  core/camera.py (context manager)
                    └──────┬───────┘
                           │ frame BGR (espelhado)
                           ▼
                    ┌──────────────┐
        ┌──────────►│  Tela atual  │  ui/menu.py  ou  modes/*.py
        │           └──────┬───────┘
        │ ESC/voltar        │ frame anotado
        │                   ▼
   ┌────┴─────┐      ┌──────────────┐
   │  MENU    │◄─────┤   Render     │  cv2.imshow + overlay (FPS)
   │ (cards)  │ clique└──────┬───────┘
   └──────────┘             │ tecla (q/ESC)
                            ▼
                     handle_key → trocar de modo / sair
```

### 3.5 Padrões aplicados (e o problema que cada um resolve)
- **Strategy/Plugin (`Mode`)** → adicionar features sem tocar no loop principal.
- **Context manager (câmera/MediaPipe)** → resolve os P0 de recurso preso.
- **Registry de modos** → menu automático e desacoplado da UI.
- **Config por dataclass** → elimina números mágicos e permite CLI/arquivo.
- **Camada de visão isolada** → trocar/atualizar MediaPipe sem afetar a lógica.

---

## 4. Interface interativa (UI/UX)

Hoje o app abre direto na webcam contando dedos. A meta é uma **tela inicial
(launcher)** onde o usuário **clica no que deseja fazer**, com navegação clara e
possibilidade de voltar.

### 4.1 Fluxo de navegação

```
                ┌─────────────────────────┐
                │        MENU INICIAL     │
                │  (cards clicáveis)      │
                └───┬───────┬───────┬─────┘
          clique ▼       ▼       ▼        ▼
     ┌───────────┐ ┌────────┐ ┌───────┐ ┌────────┐
     │ Contar    │ │ Gestos │ │ Rosto │ │ Config │
     │ Dedos     │ │        │ │ (ID)  │ │        │
     └─────┬─────┘ └───┬────┘ └───┬───┘ └───┬────┘
           │  ESC/Voltar│          │         │
           └────────────┴────►  MENU  ◄──────┘
```

Regras de UX:
- **Uma janela só** — o menu e os modos compartilham a mesma janela da webcam (transição sem "piscar").
- **ESC / botão "← Voltar"** sempre retorna ao menu; **Q** encerra o app.
- **Feedback de hover** nos cards (destaque ao passar o mouse).
- **Barra de status** no rodapé com dicas de teclado.

### 4.2 Mockup do menu inicial

```
┌──────────────────────────────────────────────────┐
│                                                    │
│            👋  Contador de Dedos                   │
│          Escolha o que deseja fazer                │
│                                                    │
│    ┌──────────┐   ┌──────────┐   ┌──────────┐      │
│    │    ✋    │   │    🤟    │   │    🙂    │      │
│    │  Contar  │   │  Gestos  │   │  Rosto   │      │
│    │  Dedos   │   │          │   │  (ID)    │      │
│    └──────────┘   └──────────┘   └──────────┘      │
│                                                    │
│    ┌──────────┐                 ┌──────────┐       │
│    │    ⚙️    │                 │    ✕     │       │
│    │  Config  │                 │   Sair   │       │
│    └──────────┘                 └──────────┘       │
│                                                    │
│   Clique em um card  •  ESC volta  •  Q encerra    │
└──────────────────────────────────────────────────┘
```

### 4.3 Escolha da tecnologia de UI

| Opção | Prós | Contras | Indicação |
|-------|------|---------|-----------|
| **OpenCV HighGUI + mouse callback** | Zero dependências novas; integra na mesma janela de vídeo; simples | Widgets "na mão" (desenhar botões e detectar clique via `setMouseCallback`); visual básico | **MVP recomendado** — mantém a stack atual |
| **PySide6 / PyQt6** | UI profissional, temas, layouts, menus nativos; vídeo embutido em `QLabel` | Dependência pesada; curva maior; cuidado com licença (PySide6 = LGPL) | **Alvo "polido"** (fase posterior) |
| **Tkinter** | Vem na stdlib; botões/menus reais; vídeo via `PIL.ImageTk` | Estético datado; integração de vídeo manual | Alternativa leve ao PySide |
| **Web (Streamlit/Gradio)** | Moderno, compartilhável, sem instalar | Webcam em tempo real é mais complexa (`streamlit-webrtc`); menos "clique e vá" local | Para uma versão web futura |

**Recomendação:** começar pelo **menu nativo em OpenCV HighGUI** (botões
desenhados + `cv2.setMouseCallback` para detectar o clique). Isso entrega a
experiência "clicável" **sem novas dependências** e reaproveita 100% do pipeline
de vídeo. Como a camada de UI está isolada (`ui/`) e os modos são plugáveis, dá
para **graduar para PySide6** depois sem tocar na lógica — só trocando o front.

```python
# ui/menu.py (esboço) — cards clicáveis sobre o frame da webcam
class Menu:
    def __init__(self, modes: list[Mode], theme: Theme):
        self.cards = layout_cards(modes)   # [(rect, mode), ...]

    def process(self, frame):
        for rect, mode in self.cards:
            draw_card(frame, rect, mode.icon, mode.name,
                      hovered=(rect == self.hovered))
        draw_status_bar(frame, "Clique em um card • ESC volta • Q encerra")
        return frame

    def on_mouse(self, event, x, y):
        self.hovered = hit_test(self.cards, x, y)
        if event == cv2.EVENT_LBUTTONDOWN and self.hovered:
            self.selected = self.hovered   # app troca para esse modo
```

### 4.4 Refino de UI/UX dos modos (aplica-se a todos)
- **Tema centralizado** (`ui/theme.py`): paleta consistente, uma fonte, tamanhos.
- **Painéis semitransparentes** atrás dos textos (legibilidade sobre qualquer fundo) — hoje o texto branco some em cenas claras.
- **FPS discreto** no canto.
- **Botão "← Voltar"** e barra de status em todos os modos.
- **Estados vazios claros:** "Nenhuma mão detectada", "Nenhum rosto cadastrado".
- **Acessibilidade:** alto contraste, textos legíveis, atalhos de teclado documentados na tela.

---

## 5. Nova funcionalidade: Identificação por Face

Objetivo: um modo **"Rosto (ID)"** que detecta rostos na webcam, compara com uma
base local de rostos **cadastrados** e mostra o nome de quem foi reconhecido
(ou "Desconhecido"). Inclui um **fluxo de cadastro** e trata **privacidade** com
seriedade — dado facial é **dado pessoal sensível** sob a LGPD.

### 5.1 Pipeline

```
frame → [detecção de face] → [recorte + alinhamento] → [embedding]
                                                            │ vetor (128/512-d)
                                                            ▼
                                          [comparar com a base cadastrada]
                                                            │ (distância < limiar?)
                                                            ▼
                                     desenhar caixa + nome  (ou "Desconhecido")
```

### 5.2 Fluxo de cadastro (enrollment)
1. Usuário entra no modo, clica em **"Cadastrar rosto"**.
2. **Tela de consentimento** (LGPD): explica o que será armazenado, onde (local) e como excluir; exige confirmação.
3. Captura N frames do rosto, digita um **nome**.
4. Extrai e salva os **embeddings** (não as fotos) na base local.
5. A partir daí, o rosto passa a ser reconhecido em tempo real.

### 5.3 Esboço de código

```python
# modes/face_id.py
class FaceId(Mode):
    name, icon = "Identificação por Face", "🙂"

    def __init__(self, db: FaceDB, detector, embedder, threshold=0.6):
        self.db, self.detector, self.embedder, self.threshold = (
            db, detector, embedder, threshold)

    def process(self, frame):
        for box in self.detector.detect(frame):
            emb = self.embedder(crop_and_align(frame, box))
            name, score = self.db.match(emb, self.threshold)
            draw_box_label(frame, box, name or "Desconhecido", score)
        return frame

    def enroll(self, name: str, frames: list) -> None:
        embs = [self.embedder(crop_and_align(f, b))
                for f in frames for b in self.detector.detect(f)]
        self.db.add(name, mean(embs))
```

```python
# storage/faces_db.py — base LOCAL, nunca versionada
class FaceDB:
    """Embeddings de rostos cadastrados (arquivo .npz + índice JSON)."""
    def add(self, name: str, embedding: np.ndarray) -> None: ...
    def match(self, embedding, threshold) -> tuple[str | None, float]: ...
    def delete(self, name: str) -> None:   # direito ao esquecimento (LGPD)
        ...
    def list(self) -> list[str]: ...
```

### 5.4 Escolha de biblioteca

| Biblioteca | Modelo | Prós | Contras |
|-----------|--------|------|---------|
| **`face_recognition` (dlib)** | ResNet 128-d | API simples, "só funciona" | Build do `dlib` pode ser chato em alguns SOs |
| **InsightFace (ONNX Runtime)** | ArcFace 512-d | Estado da arte, rápido, preciso | Setup de modelo/ONNX |
| **DeepFace** | Facenet/ArcFace/… | Alto nível, vários modelos | Pesado, muitas dependências |
| **MediaPipe Face Detection + embedding ONNX** | — | **Consistente** com a stack atual (já usamos MediaPipe) | Mais código-cola |

**Recomendação:** MVP com **`face_recognition`** pela simplicidade; se a precisão
exigir, migrar o _embedder_ para **InsightFace/ArcFace** (a interface `embedder`
isola essa troca). A **detecção** pode usar o **MediaPipe Face Detection** para
manter coerência com o resto do projeto.

### 5.5 Privacidade e LGPD (requisito, não opcional)

Dados biométricos faciais são **dados pessoais sensíveis** (LGPD, Art. 5º, II).
O modo de face **só é aceitável** com estas garantias:

- **Consentimento explícito** antes do cadastro (tela de aviso + confirmação).
- **Armazenamento apenas local** — nunca em nuvem, nunca em serviço externo.
- **Nunca versionar dados de face:** adicionar ao `.gitignore` a base e os modelos:
  ```gitignore
  # Dados biométricos e modelos — NUNCA versionar
  src/contador_dedos/storage/faces/
  *.npz
  *.dat
  *.onnx
  ```
- **Minimização:** guardar **embeddings** (vetores), não as fotos originais.
- **Direito de exclusão:** botão/comando para apagar um rosto cadastrado (`FaceDB.delete`).
- **Transparência:** seção de privacidade no README explicando o tratamento.
- **(Opcional) Criptografia em repouso** da base local.

---

## 6. Roteiro de evolução (faseado)

### Fase 0 — Higiene do repositório (rápido, alto valor) — ✅ **concluída**
1. ✅ `git rm -r --cached .idea/` e commitar a remoção (já ignorado no `.gitignore`).
2. ✅ Fixar versões em `requirements.txt` (`opencv-python==5.0.0.93`, `mediapipe==0.10.35`).
   A migração para `pyproject.toml` fica para a Fase 2, junto com o entry point.
3. ✅ Adicionar `CONTRIBUTING.md` e templates `.github/` (bug, feature, PR).

> **Próxima fase:** [Fase 1 — Correção e refatoração do núcleo](#fase-1--correção-e-refatoração-do-núcleo-p0--p1).

### Fase 1 — Correção e refatoração do núcleo (P0 + P1)
Reescrever `main.py` em funções, isolando a **lógica de contagem** (pura) da
**captura/renderização** (I/O). Esboço:

```python
# vision/landmarks.py — fim dos números mágicos
TIP_IDS = (8, 12, 16, 20)          # pontas: indicador, médio, anelar, mínimo
THUMB_TIP, THUMB_IP = 4, 3

# modes/finger_counter.py — lógica pura, testável sem webcam
def count_fingers(landmarks: list[tuple[int, int]], handedness: str) -> int:
    count = 0
    if handedness == "Right":
        count += landmarks[THUMB_TIP][0] < landmarks[THUMB_IP][0]
    else:
        count += landmarks[THUMB_TIP][0] > landmarks[THUMB_IP][0]
    for tip in TIP_IDS:
        count += landmarks[tip][1] < landmarks[tip - 2][1]
    return count
```

Entregas: corrigir **P0 #1–#7**, usar `multi_handedness`, suavizar a contagem
(anti-flicker), CLI com `argparse` (`--camera`, `--max-hands`, `--mirror`),
FPS na tela. *(Esta fase já prepara o terreno da estrutura de pacote da Fase 3.)*

### Fase 2 — Qualidade e automação (P2)
1. `pyproject.toml` com metadados, dependências e entry point (`contador-dedos`).
2. **Testes** com `pytest` sobre `count_fingers` (mãos sintéticas, sem câmera).
3. **Ruff + Black** via `pyproject.toml`; **pre-commit** com os hooks.
4. **CI (GitHub Actions):** matriz Python 3.9–3.12 rodando lint + testes.
5. Badges no README (CI, licença, Python).

### Fase 3 — Arquitetura modular (habilitadora)
Migrar para a estrutura de pacote da [Seção 3](#3-arquitetura-alvo): `Mode` (ABC),
registro de modos, `core/camera.py` como context manager, `config.py`, camada
`vision/`. **Sem mudar comportamento** — é a fundação para o menu e a face.

### Fase 4 — Interface interativa (UI/UX)
Implementar o **menu clicável** ([Seção 4](#4-interface-interativa-uiux)) em
OpenCV HighGUI: cards, hover, `setMouseCallback`, navegação ESC/Voltar, barra de
status, tema centralizado e refino de legibilidade em todos os modos.

### Fase 5 — Modos de visão adicionais
- **Reconhecimento de gestos:** joinha 👍, "paz" ✌️, "OK" 👌, mão aberta/fechada.
- **Números em Libras** (0–10) com feedback textual.
- Cada gesto/modo entra como um `Mode` novo + testes.

### Fase 6 — Identificação por Face (+ LGPD)
Implementar o modo **"Rosto (ID)"** ([Seção 5](#5-nova-funcionalidade-identificação-por-face)):
detecção, embedding, base local, fluxo de cadastro, tela de consentimento e
garantias de privacidade. Entregar com testes da camada de `FaceDB` (match/delete).

### Fase 7 — Extras
- **Feedback sonoro** ao mudar a contagem/reconhecer alguém (opcional).
- **Snapshots/gravação** (tecla `s`/`r`).
- **Modo "controle por gesto"** (mapear gestos para ações do sistema).
- **Versão web** com Streamlit/Gradio.
- **Internacionalização** (pt/en) dos rótulos.

---

## 7. Backlog priorizado

| Prioridade | Item | Fase | Esforço |
|-----------|------|------|---------|
| P0 | Validar câmera + frame; liberar recursos; tecla de saída | 1 | Baixo |
| P0 | Corrigir rótulos trocados e adicionar `cv2.flip` | 1 | Baixo |
| P0 | Usar `multi_handedness` nativo do MediaPipe | 1 | Baixo |
| P1 | Refatorar em lógica pura + I/O; CLI; FPS; anti-flicker | 1 | Médio |
| P2 | Fixar dependências / `pyproject.toml` | 0/2 | Baixo |
| P2 | Testes `pytest` da lógica de contagem | 2 | Médio |
| P2 | Ruff/Black + pre-commit + CI | 2 | Médio |
| P2 | Remover `.idea/` do versionamento | 0 | Baixo |
| **Arq.** | **Estrutura de pacote + `Mode` (ABC) + registro + config** | **3** | **Médio** |
| **UI** | **Menu clicável (cards, hover, navegação) + refino UI/UX** | **4** | **Médio** |
| P3 | Reconhecimento de gestos / Libras | 5 | Alto |
| **Face** | **Modo Identificação por Face (detecção + embedding + base)** | **6** | **Alto** |
| **Face** | **Cadastro + consentimento + garantias LGPD** | **6** | **Médio** |
| P3 | Snapshots/gravação, feedback sonoro | 7 | Médio |
| P3 | Versão web (Streamlit/Gradio) | 7 | Alto |

---

## 8. Próximos passos imediatos

1. **Fase 0** (limpeza rápida): remover `.idea/`, fixar dependências.
2. **Refatorar `main.py`** conforme a Fase 1, corrigindo todos os P0 no mesmo PR.
3. Extrair `count_fingers` e **escrever os primeiros testes**.
4. Configurar **CI + lint** para proteger a base.
5. **Fase 3 (arquitetura modular)** — é a fundação; sem ela, menu e face viram gambiarra.
6. **Fase 4 (menu clicável)** — entrega a experiência "escolha o que fazer".
7. Só então **gestos (Fase 5)** e **face (Fase 6)**, uma feature por PR, cada uma como um `Mode` com testes.

> **Princípios:** (1) estabilizar e testar o núcleo antes de expandir;
> (2) a arquitetura modular vem **antes** das features novas — é o que as torna
> baratas; (3) dado biométrico exige privacidade desde o design (LGPD), nunca
> como remendo.
