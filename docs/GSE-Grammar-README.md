# GSE-Grammar README (for IA-assistant)

## Objective
Add, **inside the existing Writing Tab**, a lightweight module that helps **English learners notice and fix the most common grammar mistakes**—without creating a new screen or workflow.

---

## 3 Key Features (MVP)
| ID | Short Name | What it Does | Why it Matters |
|--|--|--|--|
| G1 | **Grammar Lens** | Detects and highlights the 5 most frequent “trip-ups”: 3rd-person –s, articles, prepositions in/on/at, wrong verb tenses, and irregular plurals. | Learners master **patterns** that appear 80 % of the time. |
| G2 | **Micro-Feedback Popover** | On click, shows 1 rule line + 1 example + “Fix” button. | Instant, **pedagogical feedback** inside the text itself. |
| G3 | **Top Trip-Ups Panel** | Side panel that lists error counts. | Teachers see **class-wide patterns**; students see weekly progress. |

---

## Integration into the Writing Tab (Zero UX Break)

1. **Toggle** “🧠 Grammar” in the Writing Tab header (default OFF).
2. When ON:
   • Existing text is sent to **micro-service “Grammar Lens”** (endpoint `/grammar/scan`).
   • Returns array of `issues` with `offset`, `length`, `rule`, `fix`.
3. **Subtle highlight** (red/orange underline) on wrong words.
4. **Popover** on click:
   ```
   ❌ “She have …”
   ✅ “She has …”
   Rule: 3rd person → add -s
   [Fix] [Ignore]
   ```
5. **Sidebar “Top Trip-Ups”** auto-updates on save:
   ```
   • 3rd-person –s  ➜ 7 hits
   • in/on swap      ➜ 4 hits
   • childs/children ➜ 2 hits
   ```
6. **Zero extra persistence**: everything stays in the same doc; toggle is saved in `localStorage`.

---

## Dependencies
- Reuses: `EditorPane`, `documentStore`, route `/writing/:id`.
- New: service `grammarService.ts` (mock → Azure Function).
- No new screens, routes, or tokens.

---

## IA-Assistant Checklist
- [ ] Create component `GrammarToggle.tsx`.
- [ ] Create hook `useGrammarLens(text, locale)` returning `{issues, applyFix(id)}`.
- [ ] Render highlights with `<mark class="gse-grammar">`.
- [ ] Create popover `GrammarPopover.tsx`.
- [ ] Create sidebar `TopTripUpsList.tsx`.
- [ ] Add e2e test: “write error → click Fix → error disappears → Top Trip-Ups decrements”.

---
End of file.
