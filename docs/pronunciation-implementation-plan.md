# Pronunciation Feedback Implementation Plan

Este documento descreve um plano de implementação em fases para adicionar métricas de pronúncia ao projeto **HybridCoach**, alinhando-se às necessidades dos usuários identificadas em [experience_challenge_esl.md](experience_challenge_esl.md) e à visão de sistema híbrido descrita em [sophia_ia-hybrid-english-tutor.md](sophia_ia-hybrid-english-tutor.md).

## Fase 1 – MVP com ASR
- **Ação:** integrar um serviço de reconhecimento de fala (Azure Speech, Deepgram ou WhisperX) para calcular `pronunciation_score` e `word_scores`.
- **Testes:** garantir que o backend retorne os novos campos em `/api/speaking/metrics` (`pytest tests/api/test_speaking_metrics.py`).
- **Checkpoint:** Antes – apenas Speed/Clarity/Volume; Depois – API devolve também `pronunciation_score`.
- **Avaliação Humana:** amostra de áudios revisados por instrutor para validar se o escore automatizado condiz com a percepção humana.
- **Justificativa:** entrega rápida de feedback imediato valorizado pelos usuários, sem grande complexidade técnica.

## Fase 2 – Exibição na UI
- **Ação:** adicionar o badge "Pronunciation" ao lado de Speed/Clarity/Volume com tooltip de dicas.
- **Testes:** verificar renderização do badge (`pytest tests/ui/test_pronunciation_badge.py`) e inspeção manual da interface.
- **Checkpoint:** Antes – UI sem referência a pronúncia; Depois – novo badge visível com dicas contextuais.
- **Avaliação Humana:** teste de usabilidade com alunos para confirmar clareza das dicas e ausência de confusão visual.
- **Justificativa:** evidencia a importância da pronúncia e reforça boas práticas de forma acessível.

## Fase 3 – Confiabilidade e Escalonamento
- **Ação:** registrar casos de baixa confiança e permitir marcação para revisão humana.
- **Testes:** simular respostas de baixa confiança e verificar registro/flag (`pytest tests/backend/test_low_confidence.py`).
- **Checkpoint:** Antes – sem rastreio de confiança; Depois – logs e flags para revisão humana.
- **Avaliação Humana:** professores avaliam casos marcados para verificar se a flag é apropriada.
- **Justificativa:** endereça a confiança dos usuários e prepara o caminho para o modelo híbrido.

## Fase 4 – Feedback Fonêmico Avançado
- **Ação:** implementar forced alignment + GOP (Kaldi/ESPnet/Wav2Vec2) para pontuação por fonema e motivos de erro.
- **Testes:** validar cálculo de `phoneme_scores` em amostras conhecidas (`pytest tests/speech/test_gop.py`).
- **Checkpoint:** Antes – apenas pontuação por palavra; Depois – granularidade fonêmica com erros típicos.
- **Avaliação Humana:** especialistas em fonética revisam relatórios para confirmar utilidade pedagógica.
- **Justificativa:** oferece granularidade pedagógica, permitindo sugestões mais precisas de correção.

## Fase 5 – Integração Humana
- **Ação:** possibilitar que professores adicionem notas culturais/intonacionais e gerem relatórios de progresso.
- **Testes:** fluxo de criação de comentários (`pytest tests/hybrid/test_teacher_notes.py`) e revisão manual dos relatórios.
- **Checkpoint:** Antes – apenas feedback automático; Depois – comentários humanos e histórico de progresso.
- **Avaliação Humana:** revisão de professores sobre a interface de anotação e utilidade dos relatórios.
- **Justificativa:** concretiza o modelo IA + humano, agregando nuances culturais e reforçando a confiança do aluno.

## Resumo
O plano prioriza um MVP rápido com ASR para ganho imediato, evoluindo para um sistema híbrido que combina automação escalável e revisão humana, diretamente alinhado aos objetivos pedagógicos e de confiança descritos nos documentos do projeto.

Para mais contexto sobre as necessidades dos usuários e a visão híbrida, consulte também [experience_challenge_esl.md](experience_challenge_esl.md) e [sophia_ia-hybrid-english-tutor.md](sophia_ia-hybrid-english-tutor.md).
