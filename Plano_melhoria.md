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

> **Situação:** roteiro concluído até a Fase 7. Restam três itens em aberto,
> listados no fim da [Fase 7](#fase-7--extras) e no
> [backlog](#7-backlog-priorizado).

### Fase 1 — Correção e refatoração do núcleo (P0 + P1) — ✅ **concluída**

`src/main.py` foi reescrito em funções, isolando a **lógica de contagem** (pura,
testável sem webcam) da **captura/renderização** (I/O).

**P0 corrigidos:**
1. ✅ Frame validado (`check`/`None`) antes de qualquer uso, com tolerância de 30 falhas seguidas.
2. ✅ Câmera validada com `isOpened()` e mensagem de erro acionável.
3. ✅ `open_camera` é um *context manager*; `destroyAllWindows` em `finally`.
4. ✅ **Q** ou **ESC** encerram; o fechamento da janela pelo botão do sistema também.
5. ✅ Rótulos e valores realinhados — cada painel fica do lado em que aquela mão aparece.
6. ✅ `cv2.flip` ligado por padrão (`--no-mirror` desliga).
7. ✅ Lateralidade vinda do classificador do MediaPipe, não mais da heurística geométrica.

**P1 endereçados:** funções + `main()`/`__main__`, constantes nomeadas no lugar
dos números mágicos, type hints e docstrings, `AppConfig` (dataclass) no lugar
da configuração hardcoded, CLI com `argparse`, medidor de FPS e suavização
anti-flicker (`CountSmoother`). O HUD escala com a resolução e os textos têm
contorno, para continuarem legíveis em webcams 1080p e fundos claros.

> **⚠️ Mudança de API descoberta nesta fase.** A pinagem da Fase 0
> (`mediapipe==0.10.35`) **removeu a API legada `mp.solutions`**, que o código
> original usava — o app não rodava com as dependências fixadas. A camada de
> visão foi migrada para a **Tasks API** (`HandLandmarker`, modo `VIDEO`), que
> exige o modelo `hand_landmarker.task` (~7,5 MB). O download, com verificação
> de integridade (SHA-256) e escrita atômica, vive em `src/main.py` e é
> reaproveitado pelo `setup.sh` (nova etapa 4/4); o modelo fica em `models/`,
> **fora do versionamento**.
>
> Isso antecipa parte da Seção 3: `models/` já é o embrião de `storage/models/`.
> **As Fases 5 e 6 herdam a decisão** — gestos e face também passam a usar a
> Tasks API (`GestureRecognizer`, `FaceDetector`, `FaceLandmarker`), o que
> *reforça* a recomendação da Seção 5.4 de manter a detecção no MediaPipe.

Uma nota sobre a regra do polegar: o rótulo do MediaPipe e a geometria da imagem
seguem a **mesma** convenção, então a regra vale com ou sem `cv2.flip` — o
espelhamento muda apenas *a qual mão real* aquele rótulo corresponde
(`real_hand()`).

> **⚠️ Correção posterior — o sinal estava invertido.** Esta fase concluiu que
> `"Right" → tip.x > ip.x` e que, com espelho, o rótulo já era a mão real. **As
> duas coisas estavam trocadas**, e o erro sobreviveu até a Fase 7 porque as
> mãos sintéticas dos testes foram construídas na mesma convenção errada — elas
> confirmavam a inversão em vez de detectá-la.
>
> O correto: o rótulo descreve a mão **como ela aparece na imagem**. Uma mão com
> aparência de direita tem o polegar do lado esquerdo dela
> (`"Right" → tip.x < ip.x`), e com o espelho ligado quem aparece como esquerda
> é a mão direita da pessoa (`real_hand` troca).
>
> Duas evidências independentes fecharam a questão: o usuário levantou a mão
> direita com o espelho ligado e a contagem apareceu no painel "Esquerda"; e o
> código original do projeto (commit `06182fb`), que rodava **sem** espelho, já
> usava `mão direita → ponta.x < articulação.x`. `test_convencao_do_rotulo_e_a_aparencia_na_imagem`
> ancora isso e quebra primeiro se a convenção mudar.
>
> **Lição:** um fixture de teste derivado da mesma suposição que o código não
> testa a suposição. Aqui só a realidade — a câmera e a mão de alguém — podia
> arbitrar.

### Fase 2 — Qualidade e automação (P2) — ✅ **concluída**

1. ✅ `pyproject.toml` com metadados, dependências fixadas, extra `dev` e entry
   point `contador-dedos`. O `requirements.txt` virou um ponteiro (`-e .`), de
   modo que os pins têm **um único dono**.
2. ✅ **78 testes** com `pytest`, em `tests/` — contagem e lateralidade
   (`tests/helpers.py` monta mãos sintéticas), suavização, FPS, CLI, desenho e
   integridade do download do modelo (com `urlopen` substituído). A suíte roda
   **sem webcam, sem modelo e sem rede**.
3. ✅ **Ruff + Black** configurados no `pyproject.toml` (linha de 100, alvo
   `py39`, regras `E/W/F/I/B/C4/SIM/UP/RUF`) e `.pre-commit-config.yaml` com os
   dois mais os hooks de higiene — incluindo `check-added-large-files`, que
   impede commitar o modelo de 7,5 MB por acidente.
4. ✅ **CI** em `.github/workflows/ci.yml`: matriz Python 3.9–3.12 rodando lint,
   formatação e testes a cada push e PR.
5. ✅ Badges no README (CI, Python, licença, Black, Ruff).

> **Renomeação necessária.** `src/main.py` virou **`src/contador_dedos.py`**: um
> entry point instalável exige um módulo importável, e `main` no topo do
> `site-packages` colidiria com qualquer outro pacote. O caminho de execução
> antigo continua valendo (`python src/contador_dedos.py`), e agora existe
> também o comando `contador-dedos`. A Fase 3 transforma esse módulo no pacote
> `contador_dedos/` — **sem que o entry point precise mudar**, bastando o
> `__init__.py` reexportar `main`.

O `pyupgrade` (regras `UP`) modernizou as anotações para `list[...]`, `dict[...]`
e `X | None`. Isso é seguro no Python 3.9 porque o módulo usa
`from __future__ import annotations` — as anotações nunca são avaliadas em tempo
de execução. A contrapartida: `typing.get_type_hints()` sobre essas funções
falharia no 3.9. Nada no projeto faz isso, mas vale saber antes de introduzir
alguma ferramenta que inspecione tipos em runtime.

### Fase 3 — Arquitetura modular (habilitadora) — ✅ **concluída**

O módulo único virou o pacote da [Seção 3](#3-arquitetura-alvo), **sem mudar o
comportamento**: o HUD, os atalhos e a contagem continuam idênticos.

```
src/contador_dedos/
├── __init__.py            # fachada: reexporta main/App/AppConfig
├── __main__.py            # python -m contador_dedos
├── app.py                 # App: loop, roteamento de telas, teclas
├── config.py              # AppConfig (dataclass) + parse_args
├── core/
│   ├── camera.py          # Camera: context manager, espelho, tolerância a falhas
│   ├── pipeline.py        # VideoClock (timestamps crescentes) + FpsMeter
│   ├── theme.py           # paleta, fonte e escala do HUD
│   └── overlay.py         # draw_text, draw_hand_landmarks, draw_status_bar
├── vision/
│   ├── hands.py           # HandTracker: wrapper da Tasks API + real_hand
│   ├── landmarks.py       # constantes e conversão para pixels
│   └── model.py           # download genérico com SHA-256 e escrita atômica
└── modes/
    ├── base.py            # Mode (ABC): process / on_mouse / close
    ├── finger_counter.py  # a contagem (lógica pura) + sua apresentação
    └── __init__.py        # MODE_FACTORIES: o registro
```

**O que a fase destravou:**
- **`Mode` (ABC) + registro.** Acrescentar uma feature é criar a subclasse e
  somar uma linha em `MODE_FACTORIES`. O `app.py` não conhece contagem de dedos
  — só o contrato.
- **`Camera` como context manager**, com espelhamento e tolerância a frames
  vazios encapsulados; o loop ficou livre desse ruído.
- **`vision/` isolado.** É a fronteira que faltava quando `mp.solutions` sumiu
  na Fase 1: agora uma troca de biblioteca mexe em um diretório só.
- **`VideoClock`.** A regra "timestamps estritamente crescentes" do modo de
  vídeo virou uma classe testável, em vez de duas linhas fáceis de errar no
  meio do loop.
- **`download_model(destino, url, sha256)` genérico**, para a Fase 6 reusá-lo
  no modelo de rosto sem copiar código.
- **Barra de status no `app.py`**, não mais no modo: FPS e atalhos passam a ser
  responsabilidade da moldura, como a [Seção 4.4](#44-refino-de-uiux-dos-modos-aplica-se-a-todos) pede.

**Testes:** 115 (eram 78). Os novos cobrem `Camera` (com uma `VideoCapture` de
mentira), `VideoClock`, o contrato `Mode`, o registro e o roteamento do `App`.

> **Execução.** Como `src/contador_dedos.py` virou um diretório, o comando passa
> a ser **`python -m contador_dedos`** (ou `contador-dedos`). O entry point não
> mudou — o `__init__.py` reexporta `main`, exatamente como a Fase 2 previu.

> **Bug corrigido de tabela.** A renomeação da Fase 2 deixou para trás um
> `import main` no `setup.sh`, no ramo que baixa o modelo. O ramo só roda quando
> o modelo está ausente, então ninguém tinha esbarrado nele. Agora o script
> chama `ensure_hand_model(DEFAULT_MODEL_PATH)`, e esse caminho foi testado com
> o modelo removido de propósito.

**Fora do escopo desta fase:** `ui/` (menu, widgets) fica para a Fase 4, e
`storage/` (base de rostos) para a Fase 6. O modelo continua em `models/` na
raiz, e não em `storage/models/` como a Seção 3.2 desenha — escrever dentro do
pacote só funcionaria por causa do install editável, e a raiz é o lugar certo
para um artefato baixado em tempo de execução.

### Fase 4 — Interface interativa (UI/UX) — ✅ **concluída**

O app deixou de abrir direto na webcam: agora abre em um **menu clicável**, na
mesma janela, com cards, hover e navegação de volta.

```
src/contador_dedos/ui/
├── theme.py     # paleta, transparências e métricas
├── widgets.py   # Rect, hit_test, draw_text/panel/card/button/status_bar
└── menu.py      # a tela de menu (cumpre o mesmo contrato de um Mode)
```

**Entregue:**
- ✅ **Cards clicáveis** com hover destacado, montados a partir do registro de
  modos — um modo novo ganha card e atalho sem tocar na UI.
- ✅ **`cv2.setMouseCallback`** no `App`, que só registra intenção; a troca de
  tela acontece no loop, num ponto só.
- ✅ **Navegação:** ESC e o botão **← Voltar** retornam ao menu; **Q** e o card
  *Sair* encerram. No menu, ESC não faz nada — como a [Seção 4.1](#41-fluxo-de-navegação) descreve.
- ✅ **Atalhos de teclado** documentados na própria tela: o card exibe a tecla
  que o abre (`1`, `2`, …), o que resolve navegação e acessibilidade juntos.
- ✅ **Barra de status** com botão de voltar, dica de atalhos e FPS.
- ✅ **Tema centralizado** em `ui/theme.py`, com **faixas semitransparentes**
  atrás do HUD e véu sobre a webcam no menu.
- ✅ **Estado vazio:** "Nenhuma mão detectada", em vez de zeros ambíguos.

**Testes:** 170 (eram 115). Os novos cobrem geometria e hit-testing, o menu
(layout, hover, clique, atalhos) e o roteamento do `App`.

> **Limitação da HighGUI que mudou o desenho.** `cv2.putText` usa fontes
> Hershey: acentos e a seta `←` renderizam bem, mas **emoji não** — saem como
> `?`. Os ícones do mockup da [Seção 4.2](#42-mockup-do-menu-inicial) (✋ 🤟 🙂)
> foram substituídos pela **tecla de atalho** como âncora visual do card. O
> `Mode.icon` continua existindo para um front-end futuro que renderize emoji.

> **Bug de renderização corrigido.** O contorno do texto era feito desenhando-o
> por baixo com traço mais grosso — e no OpenCV o glifo *alarga* junto com a
> espessura (~16px a mais em um título). O contorno terminava depois do
> preenchimento, deixando um rastro escuro à direita, visível desde a Fase 1 e
> gritante nos textos grandes do menu. Agora o contorno repete o texto deslocado
> nas 8 direções, com a **mesma** espessura. Há um teste que mede o vazamento.

**Fora do escopo:** o card **Config** do mockup não foi incluído — não há tela de
configuração para abrir, e um card que não faz nada é pior que a sua ausência.
Os parâmetros seguem na CLI. Quando houver o que configurar, ele entra como
qualquer outra entrada do menu.

### Fase 5 — Modos de visão adicionais — ✅ **concluída** (Libras parcial)

Dois modos novos entraram, cada um como um `Mode` registrado — e o menu ganhou
os dois cards sem que a camada de UI fosse tocada.

- ✅ **Gestos** (`modes/gesture.py`): joinha, paz, OK, mão aberta e mão fechada.
- ⚠️ **Números em Libras** (`modes/libras.py`): **1 a 5**. Ver a ressalva abaixo.
- ✅ **`vision/handshape.py`**: a leitura geométrica da mão (dedos estendidos,
  régua da mão, toque entre pontas, polegar para cima), compartilhada pelos três
  modos. `count_fingers` virou a soma de `fingers_extended`.
- ✅ **Detector compartilhado**: `build_hand_tracker` cria um `HandTracker` só,
  passado a todos os modos. Antes, cada modo carregaria o modelo de novo.
- ✅ **`ValueSmoother`** (era `CountSmoother`) subiu para `core/pipeline.py` e
  virou genérico — contagens são inteiros, gestos e numerais são textos.
- ✅ **`draw_hand_readout`** em `ui/widgets.py`: o painel de duas colunas que
  gestos e Libras compartilham.

**Testes:** 247 (eram 213 após os gestos, 170 antes da fase).

> **Reconhecimento geométrico, não o do MediaPipe.** O `GestureRecognizer` da
> Tasks API traz 7 gestos prontos, mas **não inclui o "OK"** que esta seção
> pede, e exigiria um segundo modelo para baixar. Ler a geometria dos landmarks
> reaproveita o detector já carregado e mantém a lógica pura e testável.

> **⚠️ Libras: 1 a 5, e o porquê do resto ficar de fora.** Os numerais **0 e 6 a
> 10 não são reconhecidos**, e a própria tela declara isso
> (`COVERAGE_CAPTION`). De 6 a 9, as configurações não se reduzem a "N dedos
> estendidos" e **variam por região**; o 10, em várias variantes, envolve
> **movimento**, que um reconhecedor de frame único não captura. Chutar a
> configuração de uma língua real e entregá-la como correta prejudicaria
> exatamente quem usa Libras.
>
> O 1–5 segue a variante mais difundida (3 = polegar+indicador+médio;
> 4 = quatro dedos sem o polegar). **Confirmar essa variante** com uma
> referência de Libras é um item em aberto.
>
> **Para completar 6–10 depois é preciso:** (a) uma especificação confiável das
> configurações, incluindo a variante regional adotada; e (b) para os numerais
> com movimento, **análise temporal** — uma janela de frames em vez de um só,
> o que o `VideoClock` e o `ValueSmoother` já deixam ao alcance.

O que separa o modo Libras do *Contar Dedos* é *quais* dedos estão estendidos, e
não quantos — três dedos quaisquer somam 3, mas só polegar+indicador+médio é o
numeral 3. Há teste ancorando exatamente essa distinção.

### Fase 6 — Identificação por Face (+ LGPD) — ✅ **concluída**

O modo **"Rosto (ID)"** entrou como o quarto card do menu, com o pipeline da
[Seção 5.1](#51-pipeline) inteiro: detecção → alinhamento → embedding →
comparação com a base → caixa com o nome ou "Desconhecido".

```
src/contador_dedos/
├── vision/
│   ├── faces.py      # FaceTracker (BlazeFace) + alinhamento para o ArcFace
│   └── embedder.py   # protocolo Embedder + ArcFaceEmbedder (onnxruntime)
├── storage/
│   └── faces_db.py   # FaceDB: add / match / delete / names, .npz + índice JSON
└── modes/
    └── face_id.py    # as 5 telas: reconhecer, consentir, nomear, capturar, gerenciar
```

**As garantias da [Seção 5.5](#55-privacidade-e-lgpd-requisito-não-opcional), todas com teste:**
- ✅ **Consentimento explícito** — não há caminho para o cadastro que não passe
  pela tela de aviso (`test_cadastrar_passa_obrigatoriamente_pelo_consentimento`).
- ✅ **Somente local** — a camada de armazenamento não tem nenhuma chamada de rede.
- ✅ **Minimização** — grava embeddings, nunca imagens.
- ✅ **Acesso restrito** — arquivos em `0600`, verificado em teste.
- ✅ **Direito ao esquecimento** — `FaceDB.delete` e o botão *Excluir* por pessoa.
- ✅ **Fora do versionamento** — `faces/`, `*.npz`, `*.onnx`, `*.tflite`, `*.dat`.
- ✅ **Transparência** — seção *Privacidade e LGPD* no README, e um índice
  `faces.json` legível que lista os nomes cadastrados sem expor vetor algum.

**Testes:** 310 (eram 247). Cobrem `FaceDB` (match/delete/persistência/permissão/
base corrompida), a máquina de estados do modo com dublês de detector e embedder,
o alinhamento, e a extração do modelo de dentro do pacote zip.

> **Embedder: ArcFace via onnxruntime, não dlib.** A Seção 5.4 sugeria
> `face_recognition` para o MVP, com a ressalva sobre o build do `dlib` — e a
> ressalva se confirmou: **não há wheel** para este Python/arquitetura, o `dlib`
> compilaria do zero e a CI repetiria isso na matriz inteira. Fomos para o
> fallback que a própria seção previa: **ArcFace (MobileFaceNet 512-d)** sobre
> `onnxruntime`, que tem wheel pronto. A detecção usa o **MediaPipe Face
> Detector**, como a seção recomenda, mantendo a coerência com o resto da stack.

> **Carga tardia.** O detector e o ArcFace são criados **na primeira vez que o
> modo é aberto**, não no início do app: quem nunca entra no modo não paga o
> download de ~122 MB. O modo mostra o aviso um frame *antes* de bloquear —
> senão a janela congelaria sem explicação.

> **Números medidos.** Na foto de teste, a mesma pessoa com brilho alterado e
> rotação de 8° fica a **0,071** de distância; ruído aleatório fica a **1,068**.
> O limiar padrão de **0,62** separa os dois com folga larga, e é ajustável por
> `--face-threshold`. Esses números estão fixados em
> `tests/test_face_integration.py`, que é **pulado** quando os modelos não estão
> em disco — a CI nunca baixa 122 MB.

**Uma extensão no contrato `Mode`:** o cadastro precisa que o usuário digite um
nome, então `Mode.on_key(key) -> bool` foi acrescentado. A tela corrente tem a
primeira chance na tecla; devolver `True` significa "consumi" — é isso que
impede que digitar "q" em um campo de texto encerre o app.

### Fase 7 — Extras — ✅ **três de cinco** (por decisão de escopo)

A fase é um cardápio de itens independentes e de tamanhos bem diferentes; foram
escolhidos os três que cabem no app atual sem uma segunda arquitetura.

**Entregues:**
- ✅ **Snapshots/gravação** (`core/recorder.py`): **S** salva PNG, **R** liga e
  desliga a gravação em MP4, em qualquer tela. Arquivos em `capturas/`, com data
  e hora no nome. Grava o frame já anotado, e o indicador `● Gravando` é
  desenhado **depois** de o frame ir para o arquivo — o vídeo sai limpo.
- ✅ **Internacionalização pt/en** (`i18n.py`): o texto em português é a própria
  chave, então o código continua legível e uma chave sem tradução degrada para o
  português em vez de estourar. Flag `--lang`.
- ✅ **Feedback sonoro** (`core/audio.py`): bipe curto ao mudar a contagem ou
  reconhecer alguém, só na transição. **Desligado por padrão** (`--sound` liga):
  um app que apita a cada frame seria insuportável.

**Testes:** 358 (eram 310).

> **Uma rede contra rótulo esquecido.** `tests/test_i18n.py` varre o código-fonte
> atrás de `t("…")` e cobra tradução para cada literal encontrado. Sem isso, um
> rótulo novo entraria só em português e ninguém notaria até alguém rodar em
> inglês. O mesmo teste confere que os marcadores (`{n}`, `{nome}`) sobrevivem à
> tradução — trocá-los quebraria o `.format()` em tempo de execução.

> **Áudio degrada, não derruba.** O `sounddevice` depende do PortAudio, que não
> existe em todo lugar (containers, CI, servidores). O import é tardio e
> **qualquer** falha desliga o som e segue — um bipe que não toca nunca pode
> custar um frame, muito menos o app.

**Não entregues, por decisão de escopo:**
- ⬜ **Modo "controle por gesto"** — precisa de `pyautogui` como dependência
  nova, de permissão de **Acessibilidade** no macOS, e de definir quais gestos
  disparam quais ações, com trava contra disparo acidental. Merece fase própria.
- ✅ **Versão web (Streamlit)** — entregue depois, em `contador_dedos/web/`.
  O receio de "duplicar o loop de vídeo" não se concretizou: a página é uma casca
  fina sobre `HandEngine`/`FaceEngine`, que chamam os **mesmos** objetos `Mode`.
  Foi o retorno concreto da arquitetura das Fases 3–5.

  Detalhes que custaram tempo e ficam registrados:
  - `streamlit-webrtc` puxa o **PyAV**, que compila do zero na maioria das
    versões. Só a série **12.3.0** tem wheel para Python 3.9 em arm64 — daí o pin.
  - O Streamlit executa a página como **script solto**, fora do pacote: imports
    relativos quebram. A página usa imports absolutos, e há teste para isso.
  - `HTTP 200` **não** prova que a página funciona — o script só roda quando uma
    sessão conecta. Dois bugs passaram por esse teste e foram pegos pelo
    `AppTest` do Streamlit, que executa o script de verdade.
  - O processamento de frame mora no `engine`, não na página, justamente para ser
    testável sem Streamlit.

  **Escopo do modo Rosto no web:** reconhece e exclui, mas **não cadastra**. O
  cadastro depende da tela de consentimento, e duplicá-la em uma segunda moldura
  dobraria a superfície onde ela pode sair errada. O servidor sobe fixado em
  `127.0.0.1` pelo mesmo motivo.

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
| ~~P3~~ | ~~Snapshots/gravação, feedback sonoro~~ ✅ | 7 | Médio |
| P3 | Modo "controle por gesto" (pendente) | 7 | Médio |
| ~~P3~~ | ~~Versão web (Streamlit/Gradio)~~ ✅ | 7 | Alto |
| P3 | Libras: numerais 0 e 6–10 (pendente) | 5 | Alto |

---

## 8. Próximos passos imediatos

1. ~~**Fase 0** (limpeza rápida): remover `.idea/`, fixar dependências.~~ ✅
2. ~~**Refatorar `main.py`** conforme a Fase 1, corrigindo todos os P0 no mesmo PR.~~ ✅
3. ~~`count_fingers` já está extraído e puro — falta **escrever os testes** (Fase 2).~~ ✅
4. ~~Configurar **CI + lint** para proteger a base.~~ ✅
   A CI não precisa do modelo: os testes cobrem só lógica pura. Ela instala,
   isso sim, `libgl1`/`libglib2.0-0` no runner — o wheel do `opencv-python`
   (não-headless) linka libGL e o `import cv2` falharia sem elas.
5. ~~**Fase 3 (arquitetura modular)** — é a fundação; sem ela, menu e face viram gambiarra.~~ ✅
6. ~~**Fase 4 (menu clicável)** — entrega a experiência "escolha o que fazer".~~ ✅
   A aposta da Fase 3 se confirmou: o menu saiu sem tocar no loop, e um modo
   novo agora custa uma classe e uma linha no registro.
7. ~~Só então **gestos (Fase 5)** e **face (Fase 6)**, uma feature por PR, cada uma como um `Mode` com testes.~~
   Gestos, Libras (1–5) e rosto entregues. Resta o complemento de **Libras 0 e
   6–10**, que depende de referência de configurações e de análise temporal.

> **Princípios:** (1) estabilizar e testar o núcleo antes de expandir;
> (2) a arquitetura modular vem **antes** das features novas — é o que as torna
> baratas; (3) dado biométrico exige privacidade desde o design (LGPD), nunca
> como remendo.
