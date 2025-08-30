# Writing Tab — Melhorias de UX/UI e Prompt

Este documento resume as melhorias aplicadas ao Writing Tab, tanto no Frontend (layout/CSS) quanto no Backend (prompt), e como validá-las.

## Resumo das mudanças

- **Textarea estável (altura fixa)**
  - A área de texto do usuário deixou de usar `flex-grow` e passou a ter alturas explícitas com `resize-y` (o usuário pode ajustar manualmente se quiser).
  - Evita que a caixa de texto cresça quando o chat de feedback recebe mensagens longas ou em streaming.

- **Chat de feedback com scroll independente**
  - O painel de feedback (direita) agora rola dentro de si mesmo (`overflow-y-auto`) e não expande a página.
  - Foram adicionados `min-h-0` nos contêineres flex/grid para permitir que a rolagem interna funcione corretamente.

- **Markdown mais legível: cabeçalho inline + separador**
  - O backend gera um cabeçalho compacto em **uma linha** com metadados: `Essay Topic • Writing Type • Word Count`.
  - Logo abaixo do cabeçalho é inserida uma regra horizontal `---` (linha separadora), criando um divisor visual claro.

- **Espaçamento entre seções no chat**
  - No CSS do Markdown do chat, adicionamos margens entre blocos consecutivos (p, ul, ol) e estilizamos `hr` com espaçamento generoso.

- **Auto-scroll e ergonomia do Chatbot**
  - O chat rola automaticamente para o final somente quando o usuário já está “perto do fim” para não lutar com a rolagem manual.
  - Quando o usuário está longe do fim, aparece um botão “Jump to latest”.

## Arquivos alterados

- `front_end/components/WritingTab.tsx`
  - Grid/colunas com `min-h-0` para evitar crescimento indesejado e permitir rolagem interna.
  - Textarea com altura fixa e `resize-y`:
    - Classe exemplo: `w-full h-64 md:h-80 xl:h-[28rem] resize-y ... overflow-auto`.
  - Contêiner do feedback com rolagem própria: `flex-1 min-h-0 overflow-y-auto`.
  - Ajustes de JSX para manter a marcação consistente.

- `front_end/chat-markdown.css`
  - Estilo do `hr` com margem vertical maior.
  - Regras de espaçamento entre blocos consecutivos para dar “respiro” entre parágrafos e listas:
    - Seletores como `p + p`, `p + ul`, `ul + p`, `ul + ul`, etc., com `margin-top`.

- `src/core/writing_tutor.py`
  - Prompt do gerador de tópico atualizado para exigir:
    - Cabeçalho inline com metadados em uma única linha.
    - Linha horizontal `---` imediatamente após o cabeçalho.
  - Exemplo do prompt também atualizado.

- `front_end/components/Chatbot.tsx`
  - Contêiner com refs para auto-scroll suave até o final quando apropriado.
  - Botão “Jump to latest” quando o usuário não está no final do chat.
  - Normalização leve do texto do assistente para uma renderização mais limpa em Markdown.

## Como verificar as melhorias

1. **Gerar tópico (Writing Practice)**
   - Clique em “New Topic”.
   - Verifique se a primeira linha contém o cabeçalho inline `Essay Topic • Writing Type • Word Count`.
   - Verifique se há uma linha horizontal `---` logo abaixo.

2. **Escrever e avaliar**
   - Escreva um texto longo na textarea.
   - Clique em “Evaluate”. O painel de feedback deve ter rolagem independente sem aumentar a altura da textarea.

3. **Markdown e espaçamento**
   - Observe listas, parágrafos e o `hr` no feedback: o espaçamento entre blocos deve estar confortável.

4. **Auto-scroll do chat**
   - Com mensagens chegando, se estiver no fim, o chat desce automaticamente.
   - Se rolar para cima, o auto-scroll pausa e aparece “Jump to latest”.

## Notas de implementação

- **Backend**: reinicie o servidor para aplicar a mudança de prompt (`python main.py`).
- **Frontend**: o CSS/TSX atualiza com recarregamento da página (Vite/Dev Server).
- **Acessibilidade**: o botão “Jump to latest” tem `aria-label` e foco visível.

## Roadmap (opcional)

- Persistir a altura customizada da textarea no `localStorage`.
- Ajustes adicionais para mobile (ex.: `h-48 sm:h-64`).
- Validação visual para contagem de palavras solicitada pelo cabeçalho.
