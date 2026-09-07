## O que muda

<!-- Descreva a mudança em uma ou duas frases. O que este PR resolve? -->

Closes #

## Por quê

<!-- O contexto: qual problema/dor motivou a mudança. Se há uma fase do
     Plano_melhoria.md relacionada, cite aqui. -->

## Tipo de mudança

- [ ] 🐛 Correção de bug (não quebra comportamento existente)
- [ ] ✨ Nova funcionalidade
- [ ] ♻️ Refatoração (sem mudança de comportamento)
- [ ] 📖 Documentação
- [ ] 🔧 Infraestrutura / configuração

## Como testei

<!-- O projeto ainda não tem testes automatizados (Fase 2 do plano), então
     descreva o teste manual: -->

- **SO:**
- **Python:**
- **Webcam:**
- **Passos:**

## Evidência visual

<!-- Se o PR muda algo na tela, cole um print ou GIF da janela da webcam. -->

## Checklist

- [ ] O app abre a webcam e conta os dedos normalmente
- [ ] Recursos são liberados ao encerrar (`video.release()` / `destroyAllWindows()`)
- [ ] Não commitei `.idea/`, `.venv/`, `__pycache__` ou artefatos de build
- [ ] Não commitei fotos, vídeos, embeddings ou qualquer **dado biométrico**
- [ ] Novas dependências (se houver) estão **com versão fixada** no `requirements.txt`
- [ ] Li o [CONTRIBUTING.md](../blob/development/CONTRIBUTING.md)
