# Sophia AI - Streaming System Roadmap

## Implementações Concluídas

### Infraestrutura de Streaming Robusta

- ✅ **Callbacks no StreamingManager**
  - `on_chunk`, `on_complete` e `on_error` implementados e integrados com UI
  - Atualizações incrementais da interface durante streaming

- ✅ **Cancelamento cooperativo**
  - Mecanismo de `stop_event` no backend
  - `cancel()` exposto na API do frontend
  - Simplificação da UI com remoção do botão Stop explícito

- ✅ **TelemetryService atualizado**
  - Uso de `datetime.now(UTC)` em substituição ao deprecated `datetime.utcnow`
  - Eventos de telemetria para falhas, retries e heartbeats

- ✅ **Watchdog no Frontend**
  - Sistema de timeout para detectar streams inativos (`VITE_SPEAKING_STEP_TIMEOUT_SEC`)
  - Logs de console para monitorar estados do watchdog
  - Reset automático a cada chunk recebido

- ✅ **Timeout no Backend**
  - `STREAM_TIMEOUT_MS` configurável via variável de ambiente
  - Thread dedicada para monitorar inatividade em streams
  - Cancelamento automático de streams bloqueados

- ✅ **Documentação de testes de integração**
  - Guia detalhado para testar ambos os modos: imersivo e híbrido
  - Instruções para testes com rede instável e diferentes níveis de inglês

## Próximas Implementações (Prioritárias)

### Alta Prioridade

- ⏳ **Testes de integração automatizados**
  - Validação end-to-end dos fluxos de streaming em ambos os modos
  - Simulação de erros e verificação de recuperação
  - Testes com diferentes latências e qualidades de rede

- ⏳ **Integração do StreamingManager com WritingTutor**
  - Implementar fallback de texto quando o áudio falhar
  - Unificar tratamento de streaming entre componentes

- ⏳ **Roadmap documentado**
  - Manter este documento atualizado com o progresso e próximos passos

### Média Prioridade

- ⏳ **Expansão de métricas de streaming**
  - Latência entre chunks
  - Caracteres por segundo
  - Análise de tentativas e tempo total
  - Histogramas para distribuição de latência

- ⏳ **Exposição de parâmetros de streaming na UI**
  - Controles para configurações em modo de desenvolvimento
  - Validação de parâmetros
  - Ajuda contextual para desenvolvedores

### Baixa Prioridade

- ⏳ **Otimização do armazenamento temporário de áudio**
  - Sistema centralizado de diretórios temporários
  - Limpeza automática programada
  - Monitoramento de uso e quotas

- ⏳ **Indicadores de qualidade de áudio**
  - Feedback visual durante gravação
  - Detecção de clipping
  - Níveis de entrada com visualização

## Alinhamento com Plano Estratégico

Este roadmap de streaming está alinhado com a Fase 1 do plano de implementação da Sophia AI como tutor híbrido, focando na estabilização técnica, especialmente:

1. **Melhorias de estabilidade de áudio**
   - Padronização de extração de respostas de áudio
   - Implementação de retry progressivo
   - Otimização de armazenamento temporário

2. **Frontend com experiência previsível**
   - Estados de carregamento consistentes
   - Indicadores de qualidade de áudio (planejado)
   - Recuperação robusta de erros

As implementações concluídas estabelecem a base técnica necessária para avançar para as fases posteriores do plano estratégico, especialmente a integração professor-aluno e os recursos avançados de pronúncia.
