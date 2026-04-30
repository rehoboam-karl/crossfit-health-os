# Evaluation Framework — Sprint 1

Framework de avaliação em três camadas para o output do `programmer` (Session/Week/Mesocycle). Mede qualidade do treinamento prescrito **sem** depender de execução real (Layers 1 e 2) e **com** execução real (Layer 3).

Este documento descreve o estado pós-Sprint 1: framework canônico com os 8 patches críticos embutidos desde a primeira escrita, suite de regressão verde, e baseline do `HeuristicComposer-v1`.

## Sumário executivo

- **Layer 1** (deterministic): 13 métricas computáveis sobre Pydantic, sem LLM, com referências científicas. **Funcional, em uso.**
- **Layer 2** (LLM-as-judge): rubrica 6-dimensão 1-5, prompts production-ready, calibration harness. **Stub apenas — `ClaudeJudge` real fica para Sprint 2.**
- **Layer 3** (longitudinal): 7 métricas sobre `SessionResult` real (compliance, modification, PR cadence, etc.). **Funcional, em uso.**

Status no commit `7d2a74d` (PR #2 merged).

---

## Arquitetura

```
backend/app/schema/v2/
├── evaluation.py              ← Layer 1 (deterministic)
├── evaluation_judge.py        ← Layer 2 (LLM judge — stub)
├── evaluation_longitudinal.py ← Layer 3 (longitudinal)
├── eval_demo.py               ← demo end-to-end dos 3 layers
├── test_evaluation.py         ← regressão dos 8 patches (8/8 verde)
└── baselines/
    └── heuristic_composer_v1__2026-04-30.json
```

Convenção: imports diretos (`from athlete import Athlete`), igual ao resto de `v2/`. Dependência clara: o framework **lê** Pydantic (`Session`, `Week`, `Mesocycle`, `MovementLibrary`, `Athlete`, `TrainingHistory`) — não escreve, não persiste.

---

## Layer 1 — Deterministic (`evaluation.py`)

13 métricas em 4 categorias. Cada métrica retorna `MetricResult(name, category, score, raw_value, target, passed, details, reference)`.

### A. Validity (binárias, hard constraints)

| Métrica | O que checa | Referência |
|---|---|---|
| `movement_library_coverage` | 100% dos `movement_id` da sessão existem no catálogo | JMIR ERS 2025 |
| `equipment_feasibility` | Equipment requerido ⊆ equipment do atleta | — |
| `injury_safety` | Zero movimentos que violem `affected_movements` ou `affected_patterns` (via tags do catálogo) | Hard safety constraint |

### B. Volume / Intensity

| Métrica | O que mede | Threshold | Referência |
|---|---|---|---|
| `prilepin_compliance` | % blocos strength com reps em range Prilepin | ≥0.8 | Prilepin (1970s) |
| `inol_per_session` | INOL = reps/(100−%1RM) por exercício | 0.4-1.0 | Hristov (2005) |
| `acwr` | Acute:Chronic Workload Ratio | 0.8-1.3 | Gabbett (2016) |
| `foster_monotony` | mean/sd diário (com rest days padded) | <2.0 | Foster (1996) |
| `foster_strain` | total × monotony (informativa, sem cutoff) | trend | Foster (1996) |

### C. Distribution

| Métrica | O que mede | Referência |
|---|---|---|
| `modal_balance` | Distribuição M/G/W de minutos vs targets por phase | Glassman — CrossFit Theoretical Template |
| `movement_variety` | Shannon entropy normalizada de `movement_id` | Glassman — variance |
| `stimulus_distribution` | % minutos por stimulus, com checks de phase (ex: `aerobic_z2` em BASE/BUILD) | JMIR ERS 2025 |

### D. Periodization

| Métrica | O que mede | Referência |
|---|---|---|
| `progressive_overload` | Slope linear da %1RM média por semana (não-deload) | Issurin (2010) |
| `deload_presence` | ≥1 deload em mesociclo ≥4 semanas | Selye GAS |

### Agregação

```python
results = evaluate_mesocycle(mesocycle, athlete, library)
summary = summary_score(results)
# {"validity": 0|1 (hard gate), "volume_intensity": mean, "distribution": mean, "periodization": mean}
```

**Hard gating**: `validity` é binária no agregado. Qualquer uma das 3 métricas validity falhando zera a categoria inteira (Patch 3). Outras categorias: média.

---

## Layer 2 — LLM-as-Judge (`evaluation_judge.py`)

### Rubrica 6-dimensão, escala 1-5 com âncoras

1. `stimulus_coherence` — formato/movimentos/intensidade refletem o stimulus declarado
2. `personalization` — 1RMs, lesões, weak points, goals refletidos na prescrição
3. `intent_quality` — narrativa de coaching: liga estímulo↔execução, pacing/breathing/RPE
4. `progression_logic` — wave/block/conjugate identificável, deload posicionado
5. `scaling_appropriateness` — RX/Scaled/Foundation, substituições preservam stimulus
6. `safety_reasoning` — risco/benefício explícito, ajustes por lesão justificados

### Componentes

- `LLMJudge` Protocol — interface: `score_pointwise(session, dimension, context) → JudgeScore` + `compare_pairwise(a, b, dimension, context) → PairwiseResult`
- `StubJudge` — implementação dummy retornando `score=3, "STUB: implementar..."`. **Atual.**
- `POINTWISE_PROMPT` / `PAIRWISE_PROMPT` — production-ready, exigem CoT antes do score, JSON estruturado de saída
- `calibrate_judge(judge, calibration_set)` — corre judge contra ground truth humano, reporta `exact_match`, `within_one`, `mae`, `spearman_rho`
- `compare_models_pointwise(judge, sessions_by_model, dimensions, context)` — média por (modelo, dimensão)
- `tournament_pairwise(...)` — all-pairs com position bias mitigation (A/B randomizado)

### Calibração obrigatória antes de uso real

- ≥30 sessões anotadas por coach Level 2+ em escala 1-5
- Threshold: `within_one_rate ≥ 0.8` AND `spearman_rho ≥ 0.7`
- Reportar Cohen κ ou ICC

**Não há `ClaudeJudge` real nesta camada hoje.** O fluxo Sprint 2 implementa.

---

## Layer 3 — Longitudinal (`evaluation_longitudinal.py`)

Métricas sobre execução real (`SessionResult`). Janela default: 28 dias. Cada métrica retorna `LongitudinalMetric(name, value, target, interpretation, passed, n_a, details)`.

| Métrica | O que mede | Threshold |
|---|---|---|
| `compliance_rate` | % sessões executadas (não-SKIPPED) | ≥0.85 |
| `modification_rate` | % sessões **tentadas** que foram MODIFIED — denominador exclui SKIPPED | ≤0.20 |
| `skip_pattern` | Concentração de skips num único dia da semana | ≤0.40 |
| `pr_cadence` | PRs detectados na janela, **phase-aware** (BASE/BUILD: 0; PEAK: 1; TEST: 2) | varia por phase |
| `overreaching_frequency` | % semanas com signals de overreaching | ≤0.15 |
| `rpe_load_decoupling_<movement>` | Slope de RPE com %1RM constante ou caindo (proxy de fadiga) | slope ≤0.05/dia |
| `benchmark_progression_<id>` | Slope do benchmark repetido (lower/higher-is-better) | **STUB** |

### `n_a` flag

Quando não há dados, métricas retornam `value=None, n_a=True` em vez de `value=0`. O agregador `longitudinal_summary` filtra `n_a` antes de contar passed/failed:

```python
{
  "n_metrics": 7,
  "n_measurable": 5,            # filtra n_a
  "n_passed": 4,
  "n_failed": 1,
  "critical_failures": ["compliance_rate"]  # apenas compliance + overreaching contam aqui
}
```

---

## Sprint 1 — os 8 patches

Todos embutidos desde a primeira escrita, todos cobertos por `test_evaluation.py` (direta ou indiretamente).

### L1 — `evaluation.py`

**Patch 1 — Prilepin 100% edge case**
`PRILEPIN_TABLE` antiga: range 90+% era `[90, 100)` — 100% caía em `None`. Atual: `[90, 101)` inclusive. Test: `TestPrilepinZone::test_100_pct_maps_to_top_zone`.

**Patch 2 — Foster monotony/strain padding com rest days**
Antiga: 5 sessões iguais → SD=0 → monotony=∞ → score=0. Atual: pad com 0 até 7 dias. SD volta a ter sinal real. 5×60min reais + 2 rest = monotony 1.44 (saudável). Test: `TestFosterMonotonyRestDays`.

**Patch 3 — `summary_score` hard gating**
Antiga: validity virava média (1.0 + 0.0 + 1.0 = 0.667 — programa "67% válido"). Atual: 1 falha → 0.0 categoria toda. Configurável via `hard_gate_categories=("validity",)`. Test: `TestSummaryScoreGating`.

**Patch 4 — Defesa contra `mp.reps` não-int**
Antiga: `mp.reps="AMRAP"` causava `TypeError` em soma. Atual: `isinstance(mp.reps, int) and mp.reps > 0` skip silencioso. Movimentos de volume aberto (AMRAP, "12-15", "max") não fazem sentido para Prilepin/INOL — documentado como limitação. Test: `TestPrilepinReps::test_amrap_doesnt_crash`.

### L3 — `evaluation_longitudinal.py`

**Patch 5 — Imports limpos**
Removido `__import__("datetime").timedelta(...)` inline e `from datetime import timedelta` dentro de função. `timedelta` agora no topo. Removidos imports mortos (`SessionResult`, `Mesocycle`, `Session` não eram usados).

**Patch 6 — `modification_rate` denominador correto**
Antiga: denominador = todas sessões (incluindo SKIPPED). Atleta que pula 50% e modifica 100% das que executa mostrava `modification_rate=0.5` ("aceitável"). Atual: denominador = só TENTADAS. Mesmo cenário agora mostra `modification_rate=1.0` (catastrófico).

**Patch 7 — `LongitudinalMetric.n_a` flag**
Antiga: `value=0` quando "sem dados" — confunde com "0 medido". Atual: `value=None, n_a=True` explícito. Aggregator filtra antes de contar passed/failed.

**Patch 8 — `pr_cadence` phase-aware**
Antiga: 0 PRs sempre falhava (target ≥1). Programmer correto seguindo periodização block-style (volume accumulation em BASE/BUILD) era penalizado por seguir a literatura. Atual:
```python
PR_EXPECTATIONS_BY_PHASE = {
    Phase.BASE: 0, Phase.BUILD: 0, Phase.PEAK: 1, Phase.TEST: 2, Phase.DELOAD: 0,
}
```
Função agora exige `phase: Phase` arg. `evaluate_longitudinal(...)` propaga via novo arg `current_phase`.

---

## Como rodar

### Tests (regressão — 8/8 verde)

Pytest precisa rodar **fora** de `v2/` porque `v2/__init__.py` importa `macrocycle_adapter` que puxa `app.db.models` — só resolve no contexto FastAPI completo.

```bash
cp backend/app/schema/v2/test_evaluation.py /tmp/
cd /tmp && PYTHONPATH=$(pwd)/backend/app/schema/v2 \
  $(pwd)/backend/venv/bin/python -m pytest test_evaluation.py -v
```

Saída esperada: `8 passed in 0.21s`.

### Demo end-to-end

```bash
cd backend/app/schema/v2
PYTHONPATH=. ../../../venv/bin/python eval_demo.py
```

Gera mesociclo BUILD (4 semanas, 5 sessões/sem) com `HeuristicComposer-v1`, roda os 3 layers, exporta JSON.

---

## Baseline — `HeuristicComposer-v1`

Capturado em `2026-04-30T08:00:01Z`. Frozen em `baselines/heuristic_composer_v1__2026-04-30.json`.

### Layer 1 (média por categoria)

```
validity:         0.000   ← HARD GATE FIRING
volume_intensity: 0.837
distribution:     0.845
periodization:    1.000
```

### Layer 1 — métricas selecionadas (mesociclo BUILD, semana 2, dia 1)

```
✅ progressive_overload      score=1.00 raw=2.50%  (slope %1RM/sem em BUILD sweet spot)
✅ deload_presence           score=1.00            (W4 marked deload)
✅ movement_variety          score=0.93            (entropy normalizada)
✅ modal_balance (W2)        score=0.67            (M/G/W em ranges BUILD)
✅ stimulus_distribution     score=1.00
✅ foster_monotony (W2)      score=1.00 raw=1.42   (5x60min + 2 rest, sweet spot <1.5)
✅ injury_safety             score=1.00
✅ inol_per_session          score=1.00
❌ equipment_feasibility     score=0.00            ← BUG SURFACED
❌ prilepin_compliance       score=0.50            ← BUG SURFACED
✅ movement_library_coverage score=1.00
```

### Layer 3 (simulação random seed=42, 20% skip rate)

```
❌ compliance_rate    value=0.750  (esperado pelo random — 1-0.20=0.80, ruído)
✅ modification_rate  value=0.000
✅ skip_pattern       value=0.200
✅ pr_cadence         value=0.000  ← Patch 8: BUILD esperava 0 PRs, passou
✅ overreaching       value=0.000
```

---

## Bugs surfaceados pelo framework

### Bug 1: `banded_glute_bridge` em activation, sem `band` no equipment

`HeuristicComposer` prescreve `banded_glute_bridge` em todos os blocos `activation`, mas Karl (atleta de teste) não tem `band` na lista de equipamentos. O hard gate de `validity` (Patch 3) zera a categoria inteira por causa disso.

Correções possíveis:
- (a) Adicionar `band` ao equipment default de Karl
- (b) Composer escolher alternativa quando `band` não disponível (`bridge` simples?)
- (c) Catálogo marcar `band` como opcional para esse movimento

Não tocado neste PR — bug do composer/catálogo, não do eval framework.

### Bug 2: `prilepin_compliance=0.50`

Metade dos blocos strength gera reps fora do range Prilepin para a zona de %1RM. Investigação fora do escopo Sprint 1 — possíveis causas: distribuição de set×reps do composer não respeita zone caps; ou Prilepin é inadequado pra estilo CrossFit (mais variável que halterofilismo puro).

---

## Limitações conhecidas

1. **`benchmark_progression_<id>` ainda é stub** — precisa lógica de leitura histórica de benchmark results.
2. **`acwr` em mesociclos ≤4 semanas retorna 1.0 (N/A)** — precisa janela mais longa para cronical baseline.
3. **`tests` exigem PYTHONPATH manual** — `v2/__init__.py` puxa `app.db.models`. Refator possível: separar exports DB vs schema-only.
4. **Layer 2 inteira é stub** — nenhum modelo real é chamado. Sprint 2.
5. **Sem calibração contra humano** — qualquer output de L2 (mesmo após Sprint 2) é "interpretação do Claude", não "julgamento de coach". Ambos precisam de protocolo IRR para virar comparativo.
6. **Round-robin pairwise não tem self-exclusion ainda** — `tournament_pairwise` aceita qualquer judge contra qualquer composer. Sprint 2 adiciona matriz assimétrica.

---

## Sprint 2 — roadmap

Pré-requisitos: Sprint 1 verde (✅ done).

Entregáveis (~600 linhas, ~1 dia):

1. **`llm_providers.py`** — `LLMProvider` Protocol + 4 implementações (Anthropic, OpenAI, Google, DeepSeek). Schema enforcement por provider, retry, `schema_failure_rate` separado.
2. **`cost_tracker.py`** — singleton de telemetria por chamada (`provider, model, in_tokens, out_tokens, cost, latency`).
3. **`ClaudeJudge`** — substitui `StubJudge`, usa `LLMProvider`. Marca `calibration_status="uncalibrated"` em todo output.
4. **`composer_llm.py`** — wrapper que envolve `LLMProvider` na interface `MovementComposer` (paralelo ao `HeuristicComposer`).
5. **Round-robin runner** — matriz judge × composer com self-exclusion. Smoke test: 1 contexto, todos providers.

Decisões metodológicas embutidas no design (não-negociáveis):

- **Tier separation**: composers em mid-tier (Sonnet, GPT-4o, Gemini-2.5-Pro, DeepSeek-V3); judges em top-tier (Opus, GPT-5, Gemini-3-Pro). Não misturar tier no papel.
- **Self-preference mitigation**: cada composer julgado por **todos os judges exceto o da mesma família**. `score_finalₘ = média(judges não-self)`.
- **Schema enforcement**: parser tolerante + retry `n=3`. `schema_failure_rate` reportado separado do score de qualidade.

Custo estimado pilot (48 contexts × 4 composers × 3 judges = 576 chamadas): **~$65-85 total**.

Sprint 3 (paralelo, clock time longo): protocolo IRR + 2 coaches L2+ × 30 sessões. Independente do Sprint 2.

---

## Referências bibliográficas

- **Prilepin's Chart** (1970s) — Olympic weightlifting volume/intensity standards
- **Hristov, H.** (2005) — INOL formula (intensity × volume per session)
- **Foster, C.** (1996) — *Monitoring training in athletes with reference to overtraining syndrome*. Med Sci Sports Exerc 30(7).
- **Gabbett, T.** (2016) — *The training-injury prevention paradox*. Br J Sports Med 50.
- **Issurin, V.** (2010) — Block periodization
- **Glassman, G.** — CrossFit Theoretical Template (3-on-1-off, M/G/W, variance)
- **JMIR Scoping Review 2025** (e79217) — Evaluation Rigor Score for AI training prescription
- **TPS-CalcBench** — dual-axis evaluation rubric (outcome + process)
- **Liu et al.** (G-Eval, 2023) — chain-of-thought no LLM evaluator
- **Confident AI / RubricEval** — pairwise + rubric-level meta-evaluation
- **Bouchard et al.** — adherence > sofisticação programática (compliance)
- **Kraemer & Ratamess** (2004) — progressive overload outcomes
- **Selye, H.** (1956) — General Adaptation Syndrome
