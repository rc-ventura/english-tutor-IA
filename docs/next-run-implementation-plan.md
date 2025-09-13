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

- **Progress Dashboard (JSON)**
  - `src/core/progress_tracker.py` com `to_json()` e serialização de badges
  - Endpoint `GET /api/progress` em `ui/interfaces.py`
  - Frontend `ProgressTab.tsx` consumindo JSON via `api.getProgressData()`
  - Testes: `tests/test_speaking_progress.py` para XP/skills

- **Speaking XP/Skills**
  - XP/tasks: +20 XP por turno em `speaking_tutor.handle_bot_response()`
  - Pronunciation skill: atualizado com métricas em `handle_transcription()`
  - Testes unitários para validação

## Lacunas (a implementar)

- **Teacher Dashboard (frontend)**
  - Falta UI para listar/filtrar resoluções e tocar áudio de escalations.

- **Perfis de Usuário**
  - `Login.tsx` não persiste `userId` nem propaga ao backend.
  - Falta escopo por usuário para progresso e (se aplicável) escalations.

- **Manutenção periódica de áudios temporários**
  - Hoje apenas limpeza oportunista; falta scheduler opcional.

## Plano da Próxima Rodada

1) **Teacher Dashboard (prioridade alta)**
   - Frontend
     - `front_end/components/TeacherDashboard.tsx`:
       - Listar escalations (abertas/resolvidas)
       - Ver detalhes e tocar áudio
       - Marcar como resolvido
     - Integração com endpoints existentes

2) **Perfis de Usuário (prioridade média)**
   - Frontend
     - Capturar `userId` no login e propagar para chamadas
   - Backend
     - Armazenamento básico por usuário (memória/JSONL)

3) **Scheduler de limpeza de áudios (prioridade baixa)**
   - Thread periódica chamando `temp_audio_manager.maintain_tmp_audio_dir()`

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

- Dashboard de KPIs para professores
- Persistência robusta de perfis
- Badges específicas para speaking
- Integração de métricas avançadas
