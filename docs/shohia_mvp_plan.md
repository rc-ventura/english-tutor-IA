# Pronunciation Feedback Implementation Plan

> Plano de implementação em fases para adicionar **métricas de pronúncia** ao projeto **HybridCoach**, alinhado às necessidades dos usuários em [`experience_challenge_esl.md`](experience_challenge_esl.md) e à visão híbrida em [`sophia_ia-hybrid-english-tutor.md`](sophia_ia-hybrid-english-tutor.md).

---

## Visão Geral das Fases

| Fase | Foco                  | Entrega-Chave                                   | Validação                                  |
| ---- | --------------------- | ----------------------------------------------- | ------------------------------------------ |
| 1    | **MVP com ASR**       | `pronunciation_score` e `word_scores` na API    | Comparação com avaliação humana            |
| 2    | **UI**                | Badge “Pronunciation” + tooltip                 | Teste de usabilidade                       |
| 3    | **Confiabilidade**    | Registro de baixa confiança + flag para revisão | Revisão por professores                    |
| 4    | **Fonêmica**          | `phoneme_scores` (GOP + forced alignment)       | Revisão por especialistas em fonética      |
| 5    | **Integração Humana** | Notas culturais/entonacionais + relatórios      | Avaliação docente da interface e utilidade |

---

## Fase 1 – MVP com ASR

**Ação**

- Integrar um serviço de reconhecimento de fala (**Azure Speech**, **Deepgram** ou **WhisperX**) para calcular `pronunciation_score` e `word_scores`.

**Testes**

```bash
pytest tests/api/test_speaking_metrics.py
```

**Checkpoint**

> **Antes:** apenas Speed/Clarity/Volume
> **Depois:** API também retorna `pronunciation_score`

**Avaliação Humana**

- Amostra de áudios revisados por instrutor para verificar correlação entre escore automatizado e percepção humana.

**Justificativa**

- Feedback imediato valorizado pelos usuários, com baixa complexidade inicial.

---

## Fase 2 – Exibição na UI

**Ação**

- Adicionar o **badge “Pronunciation”** ao lado de Speed/Clarity/Volume, com **tooltip** contendo dicas contextuais.

**Testes**

```bash
pytest tests/ui/test_pronunciation_badge.py
```

- Inspeção manual da interface.

**Checkpoint**

> **Antes:** UI sem referência a pronúncia
> **Depois:** novo badge visível com dicas contextuais

**Avaliação Humana**

- Teste de usabilidade com alunos para confirmar clareza e ausência de ruído visual.

**Justificativa**

- Evidencia a importância da pronúncia e reforça boas práticas de forma acessível.

---

## Fase 3 – Confiabilidade e Escalonamento

**Ação**

- Registrar **casos de baixa confiança** e permitir **marcação para revisão humana**.

**Testes**

```bash
pytest tests/backend/test_low_confidence.py
```

**Checkpoint**

> **Antes:** sem rastreio de confiança
> **Depois:** logs e flags para revisão humana

**Avaliação Humana**

- Professores avaliam casos marcados para checar adequação das flags.

**Justificativa**

- Aumenta a confiança do usuário e prepara o terreno para o modelo híbrido.

---

## Fase 4 – Feedback Fonêmico Avançado

**Ação**

- Implementar **forced alignment + GOP** (Kaldi/ESPnet/Wav2Vec2) para gerar `phoneme_scores` e apontar **motivos de erro**.

**Testes**

```bash
pytest tests/speech/test_gop.py
```

**Checkpoint**

> **Antes:** pontuação por palavra
> **Depois:** granularidade fonêmica com erros típicos

**Avaliação Humana**

- Especialistas em fonética revisam relatórios para confirmar utilidade pedagógica.

**Justificativa**

- Fornece granularidade pedagógica para sugestões de correção mais precisas.

---

## Fase 5 – Integração Humana

**Ação**

- Permitir que professores adicionem **notas culturais/entonacionais** e **gerem relatórios de progresso**.

**Testes**

```bash
pytest tests/hybrid/test_teacher_notes.py
```

- Revisão manual dos relatórios.

**Checkpoint**

> **Antes:** apenas feedback automático
> **Depois:** comentários humanos e histórico de progresso

**Avaliação Humana**

- Revisão docente sobre a experiência de anotação e a utilidade dos relatórios.

**Justificativa**

- Concretiza o modelo **IA + humano**, agregando nuances culturais e reforçando a confiança do aluno.

---

## Resumo

O plano prioriza um **MVP rápido com ASR** para ganho imediato e evolui para um sistema **híbrido** que combina automação escalável e revisão humana — diretamente alinhado aos objetivos pedagógicos e de confiança descritos nos documentos do projeto.

**Referências internas**

- [`experience_challenge_esl.md`](experience_challenge_esl.md)
- [`sophia_ia-hybrid-english-tutor.md`](sophia_ia-hybrid-english-tutor.md)
