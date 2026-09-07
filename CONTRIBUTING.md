# Contribuindo com o Contador de Dedos

Obrigado pelo interesse! Este é um projeto pessoal de visão computacional
(OpenCV + MediaPipe), mas contribuições são muito bem-vindas — de correções de
bug a novos modos de detecção.

## Sumário
- [Antes de começar](#antes-de-começar)
- [Configurando o ambiente](#configurando-o-ambiente)
- [Fluxo de contribuição](#fluxo-de-contribuição)
- [Padrões de código](#padrões-de-código)
- [Mensagens de commit](#mensagens-de-commit)
- [Pull Requests](#pull-requests)
- [Reportando bugs](#reportando-bugs)
- [Dados pessoais e privacidade](#dados-pessoais-e-privacidade)

---

## Antes de começar

O rumo técnico do projeto está descrito no [`Plano_melhoria.md`](./Plano_melhoria.md):
diagnóstico, arquitetura-alvo (modos plugáveis) e o roteiro faseado. Vale a
leitura antes de propor mudanças estruturais — talvez o que você quer fazer já
esteja planejado (e valha combinar a ordem numa issue).

Regras gerais:

- **Uma feature por PR.** PRs pequenos são revisados mais rápido.
- **Abra uma issue antes** de mudanças grandes (arquitetura, nova dependência,
  novo modo), para alinhar a abordagem.
- **Não quebre o comportamento existente** sem avisar no PR.

## Configurando o ambiente

**Pré-requisitos:** Python 3.9–3.12 (faixa suportada pelo MediaPipe) e uma webcam.

```bash
git clone <url-do-seu-fork>
cd ContadorDedos
./setup.sh          # valida o Python, cria o .venv e instala as dependências
```

Executando o app:

```bash
.venv/bin/python -m contador_dedos
# ou: source .venv/bin/activate && python -m contador_dedos
```

Para desenvolver, instale também as ferramentas de qualidade e ative os hooks:

```bash
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/pre-commit install
```

Se atualizar as dependências, rode `./setup.sh --reinstall`. O script é
idempotente — pode rodar quantas vezes quiser.

> No **macOS**, autorize o acesso à câmera para o seu terminal em
> **Ajustes > Privacidade e Segurança > Câmera**.

### Dependências

As versões vivem no [`pyproject.toml`](./pyproject.toml) e são **fixadas**
(`==`) para que o build seja reproduzível — o `requirements.txt` apenas aponta
para lá (`-e .`), então há um único lugar para editar. Ao subir uma versão:

1. Altere o pin em `[project].dependencies` no `pyproject.toml`.
2. Rode `./setup.sh --reinstall`.
3. **Confirme que o app abre a webcam e conta os dedos** antes de commitar.
4. Explique no PR o motivo da atualização.

Evite adicionar dependências novas sem discutir numa issue antes — o projeto
prioriza uma stack enxuta.

## Fluxo de contribuição

1. Faça um **fork** e crie uma branch a partir de `development`:
   ```bash
   git checkout -b feat/nome-curto-da-mudanca
   ```
2. Faça suas alterações em commits pequenos e coesos.
3. **Rode os checks locais** — os mesmos que a CI executa:
   ```bash
   pytest && ruff check . && black --check .
   ```
   Com o `pre-commit install` feito, lint e formatação rodam sozinhos no commit.
4. **Adicione testes** para a lógica nova. A regra é manter a lógica pura
   separada da câmera, para que ela seja testável sem hardware — veja
   `tests/helpers.py`, que monta mãos sintéticas.

   Uma funcionalidade nova normalmente é um **`Mode`**: crie a subclasse em
   `src/contador_dedos/modes/` e registre a fábrica em `modes/__init__.py`. O
   loop principal não precisa mudar — e o card no menu, com atalho de teclado,
   aparece sozinho a partir do `name` do modo.
5. **Teste manualmente** com a webcam também: nenhum teste cobre o loop de vídeo.
6. Abra o **Pull Request** para `development`, preenchendo o template.

Prefixos de branch sugeridos: `feat/`, `fix/`, `docs/`, `refactor/`, `chore/`.

## Padrões de código

**Ruff** e **Black** são a autoridade sobre estilo — rode-os antes de abrir o
PR (ou deixe o `pre-commit` fazer isso). A configuração está no
[`pyproject.toml`](./pyproject.toml). Além do que a ferramenta cobre:

- Linhas de até **100 caracteres** (limite configurado em ambos).
- **Nomes descritivos em português** para o domínio (`contador_dedos`,
  `mao_esquerda`) — mas **sem misturar** português e inglês na mesma abstração.
- **Nada de números mágicos soltos:** dê nome aos índices de landmarks e limiares
  (`TIP_IDS`, `THUMB_TIP`) em vez de espalhar `4`, `8`, `12`.
- **Funções curtas e com responsabilidade única.** Separe a lógica pura (contagem)
  da entrada/saída (câmera, desenho na tela) — é isso que torna o código testável.
- **Docstrings e type hints** em funções públicas.
- **Sempre libere recursos:** `video.release()` e `cv2.destroyAllWindows()` ao
  encerrar, e valide o retorno de `video.read()` antes de usar o frame.

## Mensagens de commit

Escreva no **imperativo** e em português, explicando o *porquê* quando não for óbvio:

```
Corrige contagem do polegar na mão esquerda

O limiar comparava o eixo errado quando a mão estava girada.
```

O padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/)
(`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`) é bem-vindo, mas não obrigatório.

**Não commite:**

- a pasta `.idea/` ou `.vscode/` (configuração de IDE — já ignorada);
- o `.venv/`, `__pycache__/` ou qualquer artefato de build;
- credenciais, fotos, vídeos ou **dados biométricos** de qualquer tipo.

## Pull Requests

Um bom PR:

- tem **título claro** e descrição do problema que resolve;
- referencia a issue relacionada (`Closes #12`);
- inclui **prints ou GIF** quando muda algo visual (a saída da webcam);
- descreve **como você testou** (SO, versão do Python, webcam usada);
- mantém o escopo enxuto — refatoração ampla vai em PR separado.

## Reportando bugs

Abra uma issue usando o template de bug e inclua:

- **SO e versão** (ex.: macOS 15.6, Ubuntu 24.04, Windows 11);
- **versão do Python** (`python --version`);
- **passos para reproduzir** e o que você esperava que acontecesse;
- o **traceback completo**, se houver;
- modelo da webcam, se o problema for de captura.

## Dados pessoais e privacidade

O projeto prevê um modo futuro de **identificação por face** (Fase 6 do plano).
Dado facial é **dado pessoal sensível** sob a LGPD. Portanto, em qualquer
contribuição:

- **nunca** versione fotos, vídeos, embeddings ou modelos de rosto;
- todo processamento biométrico deve ser **100% local**, sem envio para nuvem;
- cadastro de rosto exige **consentimento explícito** e um caminho de exclusão.

Contribuições que quebrem essas garantias não serão aceitas.

---

Dúvidas? Abra uma issue. 💖
