# Relatório de Decisão Técnica & UX

## Pronúncia no HybridCoach – **Separar vs. Integrar**

**Data:** 23 ago 2025
**Autores:** Equipe de Produto & Engenharia
**Contexto:** funcionalidade _Speaking Imersivo_ já em produção, necessidade de feedback de pronúncia.

---

### 1. Problema levantado

- O código hoje possui `_asr_pronunciation_sphinx` (PocketSphinx) que **não agrega qualidade suficiente** e pode quebrar a experiência.
- Usuários relataram expectativas distintas:
  – _“Quero saber se estou fluente na conversa”_ (imersão)
  – _“Quero saber se meu ‘th’ está certo”_ (laboratório)

---

### 2. Decisão tomada

| Aspecto                 | Speaking Imersivo                  | Laboratório de Pronúncia Avançada         |
| ----------------------- | ---------------------------------- | ----------------------------------------- |
| **Objetivo do usuário** | Fluência, ritmo, clareza           | Ajuste fonético, redução de sotaque       |
| **Métricas entregues**  | WPM, pausas, volume, clipping      | Score fonêmico, GOP, espectrograma        |
| **Tecnologia**          | pydub + regras simples             | WhisperX / Azure + forced-alignment + GOP |
| **Carga cognitiva**     | Mínima (badge simples)             | Alta (gráficos, detalhes)                 |
| **Interação humana**    | Apenas em coaching calls agendadas | Micro-revisões assíncronas on-demand      |
| **Latência aceitável**  | <200 ms                            | 1-3 s                                     |

---

### 3. Benefícios da separação

1. **Experiência clara**Dois modos mentais: “treinar para falar” vs. “afinar minha fala”.
2. **Escalabilidade do modelo híbrido**– 90 % automatizado em cada módulo.– 10 % humano aplicado onde **realmente acrescenta valor**.
3. **Curva de aprendizado do usuário**– Iniciantes não são sobrecarregados.– Avançados têm um espaço dedicado para refinamento.
4. **Métricas separadas e acionáveis**
   – _Speaking_: conclusão de role-plays, satisfação de fluência.
   – _Pronúncia_: evolução de score fonético, taxa de upgrade premium.

---

### 4. Ações imediatas

| Semana | Tarefa                                                                  | Responsável |
| ------ | ----------------------------------------------------------------------- | ----------- |
| 1      | Remover `_asr_pronunciation_sphinx` do speaking                         | Backend     |
| 1      | Manter proxy simples (clareza, velocidade, volume)                      | Backend     |
| 2      | Criar rota `/speaking/pronunciation-detail` com Azure ou WhisperX + GOP | Speech Team |
| 2-3    | UX de “Laboratório” (badge, gráfico, botão de escalar humano)           | Design      |

---

### 5. Checklist de qualidade

- [ ] Latência < 200 ms no speaking imersivo.
- [ ] Score fonético correlacionado ≥ 0,75 com avaliação humana no laboratório.
- [ ] <5 % dos usuários confundem os dois módulos em testes de usabilidade.

---

### 6. Resumo executivo

> **Mantemos o speaking imersivo leve e rápido**, focado em fluência.
> **Criamos um laboratório separado**, com IA granular + micro-feedback humano, atendendo a quem precisa de refinamento.
> Dobra a superfície de valor do HybridCoach **sem aumentar a fricção do uso diário**.
