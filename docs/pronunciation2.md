# Relatório Técnico & UX

## **Por que separar a análise de pronúncia no HybridCoach**

**Data:** 23 de agosto de 2025
**Escopo:** decisão sobre integrar ou separar o feedback de pronúncia na funcionalidade _Speaking Imersivo_ vs. criar um _Laboratório de Pronúncia Avançada_.

---

### 1. Foco de uso & carga cognitiva

| Contexto                     | Objetivo do usuário                                                 | Carga mental desejada                          |
| ---------------------------- | ------------------------------------------------------------------- | ---------------------------------------------- |
| **Speaking imersivo**        | Treinar fluência, ritmo e clareza em calls, entrevistas, role-plays | **Mínima** – feedback rápido e visual          |
| **Laboratório de pronúncia** | Afinar sons específicos, reduzir sotaque, ver nuance fonética       | **Alta** – micro-scores, gráficos, explicações |

> Mostrar partitura durante um karaokê desvia a atenção do objetivo principal.

---

### 2. Reutilização do modelo híbrido

| Módulo                | IA (automático)                    | Humano (on-demand)                |
| --------------------- | ---------------------------------- | --------------------------------- |
| **Speaking imersivo** | 90 % – velocidade, clareza, volume | 10 % –_coaching calls_ agendadas  |
| **Laboratório**       | 90 % – WhisperX + GOP + DTW        | 10 % – micro-revisões assíncronas |

Separar mantém **escalabilidade econômica** intacta: humano só onde **realmente acrescenta valor**.

---

### 3. Curva de aprendizado personalizada

- **Iniciante** → “Estou entendível?”
- **Intermediário** → “Estou fluente?”
- **Avançado** → “Estou nativo?”

Duas features permitem **personalizar a jornada** sem sobrecarregar quem ainda não precisa de granularidade fonética.

---

### 4. Alinhamento com a missão HybridCoach

> **“IA para 90 %, humano para os 10 % que importam.”**
> Separar deixa explícito **onde a IA para e onde o humano entra**, reforçando o diferencial de **confiança** do produto.

---

### 5. Métricas & KPIs separadas

| Módulo                | KPI principal                                                                                         |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| **Speaking imersivo** | • Taxa de conclusão de role-plays`<br>`• Tempo médio de sessão `<br>`• Satisfação de fluência         |
| **Laboratório**       | • Δ score fonético em 4 semanas`<br>`• Upgrade para plano premium `<br>`• % de escalonamentos humanos |

Divisão facilita **medir o impacto real de cada frente**.

---

### Resumo executivo (1 slide)

> **Mantemos o _speaking imersivo_ leve — focado em fluência — e criamos um _Laboratório de Pronúncia_ com IA granular + humano.** > **Isso dobra a superfície de valor do HybridCoach sem aumentar a fricção do uso diário.**
