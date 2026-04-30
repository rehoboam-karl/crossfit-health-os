# cfai — Sistema de Programação CrossFit + AI

> **Para Claude Code:** este arquivo é seu contexto persistente. Leia antes de
> mexer em qualquer coisa. Decisões de design importantes estão aqui.

## O que é isto

Sistema para **gerar e avaliar programação de treino estilo HWPO/Mayhem** com
schema validado em Pydantic e framework de avaliação em 3 camadas. O objetivo
não é só gerar treinos — é poder **comparar quantitativamente** programmers
diferentes (heurísticos, Claude, GPT, Gemini) ao longo do tempo.

## Estrutura

```
src/cfai/
  workout_schema.py       Mesocycle → Week → Session → Block → MovementPrescription
  athlete.py              Athlete + 1RMs + benchmarks + injuries + load resolution
  percent_table.py        Progressões wave/linear/block multi-semana
  movements.py            Movement model + MovementLibrary (queries, filtros)
  movements_seed.py       50 movimentos com tags, scaling defaults, equipment
  session_builder.py      build_session() com derivação automática de equipment
  programmer.py           SessionPlanner + Composer Protocol + HeuristicComposer
  results.py              SessionResult, BlockResult, MovementResult (executado)
  history.py              TrainingHistory: PR detection, compliance, RPE, volume
  evaluation.py           Layer 1 — métricas determinísticas (Prilepin, ACWR, Foster)
  evaluation_judge.py     Layer 2 — LLM-as-Judge com rubrica calibrada
  evaluation_longitudinal.py  Layer 3 — métricas que precisam execução real
  examples.py             Fixture: atleta Karl + PercentTable de back squat

tests/
  validate_library.py     Sanity check da MovementLibrary
  demo_programmer.py      Gera semana inteira via planner + heurística
  demo_history.py         Feedback loop completo (plan → execute → analytics → PR)
  eval_demo.py            Aplica os 3 layers num mesociclo gerado
```

## Conceitos fundamentais (não-negociáveis)

**1. Hierarquia da programação:**
`Mesocycle → Week → Session → WorkoutBlock → MovementPrescription`

Cada nível carrega sua semântica. Não achatar — periodização precisa do nível
mesocycle (phase, primary_focus). Análise semanal precisa do nível Week
(deload flag, theme).

**2. Tipo e formato são ortogonais.**
`BlockType.METCON` + `BlockFormat.AMRAP` é diferente de `METCON + FOR_TIME_CAPPED`.
Nunca misturar em string livre — quebra queryability.

**3. Stimulus é o coração da metodologia.**
HWPO/Mayhem programam pelo *estímulo fisiológico*, não pelo movimento. O campo
`stimulus` em WorkoutBlock + `primary_stimulus` em Session é o que dá coerência
ao programa. Não é decorativo.

**4. Tags do Movement são vocabulário controlado.**
Ver `movements.TAGS_PATTERNS`. Toda adição de movimento DEVE usar tags desse
vocabulário. Injury restriction matching depende disso (atleta com lesão de
ombro evita movimentos com tag `overhead` automaticamente).

**5. LoadSpec discriminado.**
4 tipos: `absolute_kg`, `percent_1rm`, `percent_bw`, `bodyweight`, mais `rpe`
e `ahap` que não resolvem para kg fixo. `percent_1rm` SEMPRE exige
`reference_lift`. Validação obriga.

**6. Scaling é por movimento, não por bloco.**
Um metcon pode ter pull-ups Rx + box jumps Scaled. Cada `MovementPrescription`
tem seu próprio dict de scaling tiers.

**7. Validações estruturais são preventivas.**
Pydantic rejeita: sessão sem warm_up, 2x strength_primary, cooldown no meio,
movimento com volume duplo (reps + time), recovery com metcon, etc. Não
remover validações sem entender o porquê.

## Decisões arquiteturais importantes

**Composer plugável (programmer.py).**
`MovementComposer` é Protocol. `HeuristicComposer` é rule-based (default).
`ClaudeComposer` é stub. O point é: o **scaffold de blocos** é determinístico
(template selection + scaffold de BlockTypes); a **criatividade** (escolha de
movimentos, intent narrativo, scaling) entra via composer. Trocar composer
não muda a estrutura da semana.

**equipment_required derivado, não declarado.**
`session_builder.build_session()` calcula automaticamente via
`library.derive_equipment(movement_ids)`. Não construir Session diretamente
fora de exemplos didáticos. Declaração manual fica defasada.

**PRs detectados via duas fontes (com dedupe).**
`history.detect_prs()` busca tanto em `BlockResult.actual_score` (string + load)
quanto em `MovementResult` com reps=1. Dedupe por
`(movement_id, achieved_at, value_kg)`. Não remover dedupe.

**`apply_prs_to_athlete` retorna nova instância.**
Pydantic `model_copy(update=...)`. Imutabilidade vale ouro pra reproducibilidade.
NUNCA mutar Athlete in-place.

**Avaliação em 3 layers, não amontoar tudo:**
- L1 = determinístico, fundamentação científica explícita
- L2 = LLM judge para qualitativo (precisa CALIBRAÇÃO antes de uso real)
- L3 = longitudinal, precisa execução simulada/real

## Bibliografia que ancora o framework

- **Prilepin's Chart** (1970s): volume ótimo por zona %1RM
- **Hristov INOL** (2005): `reps / (100 - %1RM)`, ideal 0.4-1.0
- **Gabbett ACWR** (2016): sweet spot 0.8-1.3, >1.5 risco lesão
- **Foster Monotony/Strain** (1996): mean/sd, >2.0 alerta
- **Glassman CrossFit Theoretical Template**: variance principle, MGW
- **JMIR Scoping Review 2025** (e79217): Evaluation Rigor Score (ERS)
- **G-Eval, RubricEval, JudgeBench**: LLM-as-Judge state-of-the-art

## Workflow para rodar o sistema

```bash
# Setup (Python 3.11+)
pip install -e ".[dev]"

# Sanity checks
pytest tests/validate_library.py
python tests/demo_programmer.py    # gera semana
python tests/demo_history.py        # feedback loop completo
python tests/eval_demo.py           # avaliação 3 layers
```

## Próximos passos planejados (em ordem)

1. **`ClaudeJudge` real** (substitui StubJudge em `evaluation_judge.py`).
   Pseudocódigo já está no docstring `CLAUDE_JUDGE_REFERENCE_IMPL`.

2. **Test set congelado** — 20-30 `ProgrammingContext` cobrindo
   phases × profiles × constraints. JSON fixo em `tests/fixtures/`.

3. **Calibration harness** com coach humano. ≥30 sessões em escala 1-5.
   Reportar Cohen κ ou Spearman ρ ≥0.7 antes de uso em produção.

4. **`ClaudeComposer` real** (substitui stub em `programmer.py`).

5. **Pilot study comparativo:** Claude Opus 4.7 vs. Sonnet 4.6 vs. GPT-5
   vs. Gemini-3-Pro como composers, melhor judge avaliando todos no mesmo
   test set congelado.

6. **Movement library expansion** 50 → 100+ (Strongman, complexos olímpicos).

## O que NÃO fazer

- Não criar Session diretamente fora dos exemplos didáticos — sempre
  via `build_session()`.
- Não adicionar movimento sem tags do vocabulário em `TAGS_PATTERNS`.
- Não mexer em validações estruturais do Pydantic sem entender porquê
  estão ali (cada uma resolveu um bug real).
- Não remover dedupe de PRs em `history.detect_prs()`.
- Não declarar `equipment_required` manualmente.
- Não usar `Stimulus` como decoração — toda escolha de bloco
  deveria mapear pra um stimulus claro.

## Convenções

- Type hints sempre
- Pydantic v2 (`model_validator`, `model_copy`, `model_dump_json`)
- Factory functions para Pydantic models complexos (ex.: `build_session`,
  `build_session_result`)
- Imports relativos dentro do pacote (`from .workout_schema import ...`)
- Tests em `tests/` importam como `from cfai.X import Y`
