# Sophia AI — Próxima Rodada de Implementações

Este README resume o que já está implementado e o que será implementado na próxima rodada, com foco em: estabilidade de áudio/streaming, manutenção de áudios temporários, métricas, escalations e evolução do Progress Dashboard, Teacher Dashboard e Perfis de Usuário.

## O que já temos (Confirmado)

- **Streaming resiliente (backend)**
  - `src/infra/streaming_manager.py` com retry/backoff, heartbeat, timeout e cancelamento cooperativo.
  - Testes: `tests/test_streaming_manager.py`, `tests/test_streaming_manager_timeout.py`.

- **Speaking (frontend)**
  - `front_end/components/SpeakingTab.tsx` com watchdog de stream e cancelamento.
  - `front_end/services/api.ts` com callbacks de streaming e cancel.

- **Áudio e fallback (backend)**
  - `src/services/openai_service.py` e `src/utils/audio.py` com extração robusta de texto/áudio e fallback para texto quando áudio falha.

- **Métricas de fala (backend)**
  - Endpoint: `ui/interfaces.py` (`/api/speaking/metrics`).
  - Análise de pronúncia: `src/utils/audio.py:analyze_pronunciation_metrics()`.

- **Escalation (backend)**
  - `src/core/escalation_manager.py` + rotas REST em `ui/interfaces.py`:
    - criar/listar/obter/resolver e `/{id}/audio`.
  - Testes: `tests/test_escalation_manager.py`.

- **Áudios temporários**
  - `src/infra/temp_audio_manager.py` com limpeza por idade/contagem/tamanho.
  - Uso oportunista em `src/utils/audio.py:save_audio_to_temp_file()`.

- **Progress Dashboard (HTML atual)**
  - Backend: `src/core/progress_tracker.py` com HTML (`html_dashboard()`).
  - UI Gradio na aba Progress em `ui/interfaces.py`.
  - Frontend tem `front_end/components/ProgressTab.tsx` e `front_end/types.ts (ProgressData)`.

## Lacunas (a implementar)

- **Progress JSON endpoint**
  - Backend ainda não expõe `GET /api/progress` em JSON.
  - `ProgressTab.tsx` espera `ProgressData` (JSON), mas hoje consome HTML via `getProgressHtml()`.

- **Cálculo de nível/thresholds e badges no JSON**
  - `ProgressTracker` precisa fornecer `level`, `xpForCurrentLevel`, `xpForNextLevel` e `badges` com `unlocked`.

- **Teacher Dashboard (frontend)**
  - Falta UI para listar/filtrar resoluções e tocar áudio de escalations.

- **Perfis de Usuário**
  - `Login.tsx` não persiste `userId` nem propaga ao backend.
  - Falta escopo por usuário para progresso e (se aplicável) escalations.

- **Manutenção periódica de áudios temporários**
  - Hoje apenas limpeza oportunista; falta scheduler opcional.

## Plano da Próxima Rodada

1) **Progress em JSON (prioridade alta)**
   - Backend
     - `src/core/progress_tracker.py`: adicionar `to_json()` com:
       - `xp`, `level`, `xpForCurrentLevel`, `xpForNextLevel`, `tasksCompleted`.
       - `skills` e `badges` com `{ name, description, unlocked, iconName }`.
     - `ui/interfaces.py`: criar `GET /api/progress` retornando `application/json`.
   - Frontend
     - `front_end/services/api.ts`: substituir `getProgressHtml()` por `getProgressData()` (REST JSON).
     - `front_end/components/ProgressTab.tsx`: consumir `ProgressData` e remover dependência de HTML.
     - Validar tipos em `front_end/types.ts`.

2) **Teacher Dashboard (prioridade média)**
   - Frontend
     - Novo `front_end/components/TeacherDashboard.tsx`:
       - Listar escalations (abertas/resolvidas), ver detalhes, tocar áudio e resolver.
       - Usar endpoints: `GET /api/escalations`, `GET /api/escalations/{id}/audio`, `POST /api/escalations/{id}/resolve`.
     - Navegação
       - Adicionar tab no `front_end/App.tsx` e item no `front_end/components/Sidebar.tsx`.

3) **Perfis de Usuário (prioridade média)**
   - Frontend
     - `front_end/components/Login.tsx`: capturar `userId` (e-mail), salvar em `localStorage`.
     - Incluir `userId` nas chamadas REST que precisam de escopo.
   - Backend
     - Prover armazenamento simples por usuário (in-memory/JSONL) para progresso: map `userId -> ProgressTracker`.

4) **Scheduler de limpeza de áudios (prioridade baixa/opcional)**
   - Backend
     - Thread/cron simples no startup para chamar `maintain_tmp_audio_dir()` periodicamente (env-configurável).

## Contrato de API Proposto (Progress)

- `GET /api/progress` → 200 JSON
```json
{
  "xp": 1250,
  "level": 5,
  "xpForCurrentLevel": 1000,
  "xpForNextLevel": 1500,
  "tasksCompleted": 42,
  "skills": { "grammar": 68, "vocabulary": 74, "pronunciation": 63 },
  "badges": [
    { "name": "First Steps", "description": "First session completed", "unlocked": true,  "iconName": "First Steps" },
    { "name": "Rising Star", "description": "500 XP reached",       "unlocked": true,  "iconName": "Rising Star" },
    { "name": "Master",      "description": "Level 10 achieved",     "unlocked": false, "iconName": "Master" }
  ]
}
```

## Verificação e Testes

- **Backend**
  - Unit para `to_json()` cobrindo limites (xp=0, quase próximo nível, badges).
  - Teste do `GET /api/progress` (200 + schema básico).
- **Frontend**
  - Mock de `getProgressData()` para teste de render no `ProgressTab`.
  - Manual: abrir aba Progress, verificar barras, XP/nível, badges e refresh.

## Riscos & Mitigações

- **Desalinhamento JSON vs tipos** → manter exemplo canônico e testes.
- **Dependência do HTML antigo** → migrar ProgressTab para JSON; deprecar HTML se não for mais usado.

## Critérios de Aceite

- `GET /api/progress` ativo e documentado.
- `ProgressTab.tsx` usando JSON sem erros.
- Teacher Dashboard disponível com listar/visualizar/resolve e áudio tocável.
- `userId` básico persistido e disponível no frontend (plumbing pronto para backend).

## Próximos (posteriores à rodada)

- Persistência robusta de perfis (db/arquivo por usuário).
- KPIs no Teacher Dashboard e filtros avançados.
- Scheduler de limpeza ajustável por ambiente com métricas de housekeeping.
