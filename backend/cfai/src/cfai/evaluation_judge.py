"""
Evaluation Layer 2 — LLM-as-Judge com rubrica.

Avalia dimensões QUALITATIVAS que não podem ser computadas deterministicamente:
- coerência stimulus↔formato↔movimentos
- personalização para o atleta
- qualidade do coaching narrative (intent)
- lógica de progressão semana-a-semana
- adequação de scaling

Referências:
- JMIR 2025 (e79217) — recomenda LLM-as-judge calibrado contra experts
- TPS-CalcBench — dual-axis (outcome + process), 8-dimension rubric
- G-Eval (Liu 2023) — chain-of-thought no evaluator
- RubricEval — rubric-level meta-evaluation
- Liu et al. (Confident AI) — pairwise comparison para A/B test

Práticas implementadas:
1. Critérios decompostos (1 dimensão por chamada — não confundir o judge)
2. Rubrica explícita 1-5 com âncoras
3. CoT obrigatório no prompt (judge explica antes de scorar)
4. JSON estruturado validado
5. Pairwise mode para comparar modelos diretamente
6. Position bias mitigation (randomiza ordem em pairwise)

CALIBRAÇÃO necessária antes de uso em produção:
- Domain expert (coach Level 2+) anota ≥30 sessões em escala 1-5
- LLM judge é avaliado contra esse ground truth
- Reportar agreement (Cohen κ ou Spearman ρ) — meta ≥0.7
"""

import json
import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol

from .workout_schema import Session


# ============================================================
# DIMENSÕES DA RUBRICA
# ============================================================

class JudgeDimension(str, Enum):
    STIMULUS_COHERENCE = "stimulus_coherence"
    PERSONALIZATION = "personalization"
    INTENT_QUALITY = "intent_quality"
    PROGRESSION_LOGIC = "progression_logic"
    SCALING_APPROPRIATENESS = "scaling_appropriateness"
    SAFETY_REASONING = "safety_reasoning"


# Rubrica com âncoras explícitas para cada nível
RUBRIC: dict[JudgeDimension, dict[int, str]] = {
    JudgeDimension.STIMULUS_COHERENCE: {
        1: "Formato/movimentos contradizem o stimulus declarado",
        2: "Conexão fraca entre stimulus e prescrição",
        3: "Coerente mas genérico — sem otimização do estímulo",
        4: "Bem alinhado, escolhas defensáveis",
        5: "Stimulus rigorosamente expresso na prescrição (formato, "
           "movimentos, intensidade, intervalos)",
    },
    JudgeDimension.PERSONALIZATION: {
        1: "Prescrição genérica, ignora perfil do atleta",
        2: "Considera 1-2 atributos (ex: só equipment)",
        3: "Considera múltiplos atributos sem sutileza",
        4: "Personalização visível em escolhas e cargas",
        5: "Personalização rica: 1RMs, lesões, weak points, goals, "
           "histórico recente — todos refletidos",
    },
    JudgeDimension.INTENT_QUALITY: {
        1: "intent ausente ou genérico ('faça forte')",
        2: "Descreve o que mas não o porquê",
        3: "Justificativa razoável mas sem especificidade",
        4: "intent claro, específico, ensinável",
        5: "intent excepcional: liga estímulo↔execução, "
           "menciona pacing/breathing/RPE alvo, evita armadilhas",
    },
    JudgeDimension.PROGRESSION_LOGIC: {
        1: "Sem progressão ou progressão ilógica entre semanas",
        2: "Progressão presente mas inconsistente",
        3: "Progressão clara em 1 dimensão (ex: só carga)",
        4: "Progressão multi-dimensional coerente",
        5: "Progressão sofisticada: wave/block/conjugate identificável, "
           "deload posicionado, retest planejado",
    },
    JudgeDimension.SCALING_APPROPRIATENESS: {
        1: "Scaling ausente ou inadequado para o nível",
        2: "Scaling presente mas não preserva stimulus",
        3: "Scaling preserva stimulus em alguns movimentos",
        4: "Scaling preserva stimulus consistentemente",
        5: "Scaling exemplar: tier RX/Scaled/Foundation, "
           "substituições mantêm estímulo+intensidade",
    },
    JudgeDimension.SAFETY_REASONING: {
        1: "Decisões de segurança ausentes ou erradas",
        2: "Considera contraindicação óbvia mas não explica",
        3: "Reconhece restrição e ajusta sem detalhar",
        4: "Justifica ajustes por lesão, sugere alternativas",
        5: "Reasoning explícito sobre risco/benefício, "
           "preserva intenção do treino respeitando restrições",
    },
}


# ============================================================
# CONTAINERS
# ============================================================

@dataclass
class JudgeScore:
    dimension: JudgeDimension
    score: int                          # 1-5 Likert
    reasoning: str
    judge_model: str
    confidence: Optional[float] = None  # 0-1, opcional


@dataclass
class PairwiseResult:
    dimension: JudgeDimension
    winner: str                          # "A", "B", "tie"
    reasoning: str
    judge_model: str


# ============================================================
# JUDGE INTERFACE
# ============================================================

class LLMJudge(Protocol):
    """Interface para LLM judge — implementar com Claude/GPT/Gemini API."""

    def score_pointwise(
        self, session: Session, dimension: JudgeDimension, context: dict,
    ) -> JudgeScore: ...

    def compare_pairwise(
        self, session_a: Session, session_b: Session,
        dimension: JudgeDimension, context: dict,
    ) -> PairwiseResult: ...


# ============================================================
# PROMPTS (production-ready)
# ============================================================

POINTWISE_PROMPT = """Você é um coach CrossFit Level 3 avaliando uma sessão de treino.

Contexto do atleta:
{athlete_context}

Sessão prescrita (JSON):
{session_json}

Avalie EXCLUSIVAMENTE a dimensão: **{dimension}**

Rubrica (1-5):
{rubric}

Instruções:
1. Pense passo-a-passo sobre os elementos da sessão relevantes para esta dimensão.
2. Identifique evidências específicas (cite blocos por order).
3. Compare contra a rubrica.
4. Atribua score inteiro 1-5.
5. Output JSON estrito:
{{"reasoning": "...", "score": <int>, "evidence": ["block_3: ...", ...]}}

NÃO avalie outras dimensões. NÃO seja influenciado por extensão da resposta.
"""


PAIRWISE_PROMPT = """Você é um coach CrossFit Level 3 comparando duas sessões.

Contexto: {athlete_context}

Sessão A (JSON): {session_a_json}
Sessão B (JSON): {session_b_json}

Dimensão de comparação: **{dimension}**
Rubrica: {rubric}

Qual sessão é melhor NESTA dimensão especificamente?
- Não considere preferência estilística
- Cite evidências de ambas as sessões
- "tie" só se rigorosamente equivalentes

Output JSON: {{"reasoning": "...", "winner": "A"|"B"|"tie", "evidence_a": [...], "evidence_b": [...]}}
"""


# ============================================================
# STUB IMPLEMENTATION
# ============================================================

class StubJudge:
    """Implementação stub para teste de pipeline.
    Substituir por ClaudeJudge / GPTJudge / GeminiJudge em produção.
    """

    def __init__(self, model_name: str = "stub-judge"):
        self.model_name = model_name

    def score_pointwise(
        self, session: Session, dimension: JudgeDimension, context: dict,
    ) -> JudgeScore:
        return JudgeScore(
            dimension=dimension,
            score=3,
            reasoning="STUB: implementar chamada à API com POINTWISE_PROMPT",
            judge_model=self.model_name,
        )

    def compare_pairwise(
        self, session_a: Session, session_b: Session,
        dimension: JudgeDimension, context: dict,
    ) -> PairwiseResult:
        return PairwiseResult(
            dimension=dimension,
            winner="tie",
            reasoning="STUB: implementar com PAIRWISE_PROMPT",
            judge_model=self.model_name,
        )


# ============================================================
# LLM PROVIDER JUDGE — implementação real, parametrizada por LLMProvider
# ============================================================

import json as _json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_providers import LLMProvider


SYSTEM_INSTRUCTION_JUDGE = (
    "Você é um coach CrossFit Level 3. Avalia sessões de treino com rigor "
    "técnico, citando evidências específicas. Output sempre JSON válido."
)


class LLMProviderJudge:
    """Judge real que delega chamadas de scoring para qualquer LLMProvider.

    Substitui StubJudge em produção. Mantém o contrato `score_pointwise` /
    `compare_pairwise`. Qualquer provider (Anthropic/OpenAI/DeepSeek/Groq/
    Minimax) compatível com `LLMProvider` pode ser usado.

    `calibration_status` deve permanecer `"uncalibrated"` até protocolo de
    IRR ≥30 sessões com coach Level 2+ ter `within_one_rate ≥ 0.8` e
    `spearman_rho ≥ 0.7`. Outputs antes disso não devem ser comparados
    contra ground truth humano.
    """

    def __init__(
        self,
        provider: "LLMProvider",
        calibration_status: str = "uncalibrated",
        max_retries: int = 3,
    ):
        self.provider = provider
        self.calibration_status = calibration_status
        self.judge_model = provider.name
        self.max_retries = max_retries

    def score_pointwise(
        self, session, dimension: JudgeDimension, context: dict,
    ) -> JudgeScore:
        prompt = POINTWISE_PROMPT.format(
            athlete_context=_json.dumps(context, default=str),
            session_json=(
                session.model_dump_json(indent=2)
                if hasattr(session, "model_dump_json")
                else _json.dumps(session, default=str)
            ),
            dimension=dimension.value,
            rubric=_json.dumps(RUBRIC[dimension], ensure_ascii=False, indent=2),
        )

        last_resp = None
        for attempt in range(self.max_retries):
            resp = self.provider.complete(
                system=SYSTEM_INSTRUCTION_JUDGE,
                user=prompt,
                json_mode=True,
                temperature=0.0,
                max_tokens=4096,
                label=f"judge_pointwise_{dimension.value}",
            )
            last_resp = resp
            if not resp["schema_failure"] and resp["parsed"]:
                data = resp["parsed"]
                if "score" in data and isinstance(data["score"], (int, float)):
                    return JudgeScore(
                        dimension=dimension,
                        score=int(round(float(data["score"]))),
                        reasoning=str(data.get("reasoning", "")),
                        judge_model=self.judge_model,
                    )
            # else retry

        # Esgotou retries — devolve um JudgeScore degradado, marcando o problema
        return JudgeScore(
            dimension=dimension,
            score=0,
            reasoning=(
                f"[SCHEMA FAILURE after {self.max_retries} attempts] "
                f"Last raw content: {(last_resp['content'] if last_resp else '')[:300]}"
            ),
            judge_model=self.judge_model,
        )

    def compare_pairwise(
        self, session_a, session_b,
        dimension: JudgeDimension, context: dict,
    ) -> PairwiseResult:
        prompt = PAIRWISE_PROMPT.format(
            athlete_context=_json.dumps(context, default=str),
            session_a_json=(
                session_a.model_dump_json(indent=2)
                if hasattr(session_a, "model_dump_json")
                else _json.dumps(session_a, default=str)
            ),
            session_b_json=(
                session_b.model_dump_json(indent=2)
                if hasattr(session_b, "model_dump_json")
                else _json.dumps(session_b, default=str)
            ),
            dimension=dimension.value,
            rubric=_json.dumps(RUBRIC[dimension], ensure_ascii=False, indent=2),
        )
        for _ in range(self.max_retries):
            resp = self.provider.complete(
                system=SYSTEM_INSTRUCTION_JUDGE, user=prompt,
                json_mode=True, temperature=0.0, max_tokens=4096,
                label=f"judge_pairwise_{dimension.value}",
            )
            if resp["parsed"] and "winner" in resp["parsed"]:
                d = resp["parsed"]
                w = d["winner"]
                if w in ("A", "B", "tie"):
                    return PairwiseResult(
                        dimension=dimension,
                        winner=w,
                        reasoning=str(d.get("reasoning", "")),
                        judge_model=self.judge_model,
                    )
        return PairwiseResult(
            dimension=dimension, winner="tie",
            reasoning="[SCHEMA FAILURE] retries esgotados",
            judge_model=self.judge_model,
        )


# ============================================================
# CALIBRATION HARNESS
# ============================================================

@dataclass
class CalibrationItem:
    """Item de calibração: sessão + score humano (ground truth)."""
    session: Session
    dimension: JudgeDimension
    expert_score: int                    # 1-5 do coach humano
    expert_reasoning: Optional[str] = None
    context: Optional[dict] = None


def calibrate_judge(
    judge: LLMJudge,
    calibration_set: list[CalibrationItem],
) -> dict:
    """Roda judge contra ground truth e calcula agreement.

    Reporta:
    - exact_match: % de scores idênticos
    - within_one: % com diferença ≤1 (mais tolerante)
    - mean_abs_error: erro absoluto médio
    - spearman_rho: correlação de ranking (importante p/ pairwise)
    """
    judge_scores, expert_scores = [], []
    per_item = []

    for item in calibration_set:
        js = judge.score_pointwise(
            item.session, item.dimension, item.context or {},
        )
        judge_scores.append(js.score)
        expert_scores.append(item.expert_score)
        per_item.append({
            "dimension": item.dimension.value,
            "expert": item.expert_score,
            "judge": js.score,
            "diff": abs(js.score - item.expert_score),
        })

    n = len(calibration_set)
    exact = sum(1 for j, e in zip(judge_scores, expert_scores) if j == e) / n
    within_one = sum(1 for j, e in zip(judge_scores, expert_scores)
                     if abs(j - e) <= 1) / n
    mae = sum(abs(j - e) for j, e in zip(judge_scores, expert_scores)) / n

    # Spearman ρ (ranking correlation)
    def rank(values: list[int]) -> list[float]:
        sorted_idx = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        for r, i in enumerate(sorted_idx):
            ranks[i] = r + 1
        return ranks

    if len(set(judge_scores)) > 1 and len(set(expert_scores)) > 1:
        rj = rank(judge_scores)
        re = rank(expert_scores)
        mean_rj, mean_re = sum(rj) / n, sum(re) / n
        num = sum((a - mean_rj) * (b - mean_re) for a, b in zip(rj, re))
        den_a = (sum((a - mean_rj) ** 2 for a in rj)) ** 0.5
        den_b = (sum((b - mean_re) ** 2 for b in re)) ** 0.5
        spearman = num / (den_a * den_b) if (den_a * den_b) > 0 else 0.0
    else:
        spearman = 0.0

    return {
        "n_items": n,
        "exact_match_rate": round(exact, 3),
        "within_one_rate": round(within_one, 3),
        "mean_abs_error": round(mae, 3),
        "spearman_rho": round(spearman, 3),
        "passes_threshold": within_one >= 0.8 and spearman >= 0.7,
        "per_item": per_item,
    }


# ============================================================
# COMPARISON HARNESS — comparar modelos
# ============================================================

def compare_models_pointwise(
    judge: LLMJudge,
    sessions_by_model: dict[str, list[Session]],
    dimensions: list[JudgeDimension],
    context: dict,
) -> dict:
    """Avalia N sessões de cada modelo nas dimensões dadas.
    Retorna média por (modelo, dimensão).
    """
    out: dict[str, dict[str, float]] = {}
    for model_name, sessions in sessions_by_model.items():
        out[model_name] = {}
        for dim in dimensions:
            scores = [
                judge.score_pointwise(s, dim, context).score
                for s in sessions
            ]
            out[model_name][dim.value] = (
                sum(scores) / len(scores) if scores else 0.0
            )
    return out


def tournament_pairwise(
    judge: LLMJudge,
    sessions_by_model: dict[str, list[Session]],
    dimensions: list[JudgeDimension],
    context: dict,
) -> dict:
    """All-pairs tournament. Para cada par de modelos, joga N rodadas.
    Position bias mitigation: A/B aleatórios.

    Retorna win-rate por modelo (aggregado entre dimensões).
    """
    models = list(sessions_by_model.keys())
    wins: dict[str, int] = {m: 0 for m in models}
    games = 0

    for i, ma in enumerate(models):
        for mb in models[i+1:]:
            sa, sb = sessions_by_model[ma], sessions_by_model[mb]
            n = min(len(sa), len(sb))
            for k in range(n):
                for dim in dimensions:
                    # Randomiza ordem
                    if random.random() < 0.5:
                        first, second, first_name, second_name = sa[k], sb[k], ma, mb
                    else:
                        first, second, first_name, second_name = sb[k], sa[k], mb, ma
                    res = judge.compare_pairwise(first, second, dim, context)
                    games += 1
                    if res.winner == "A":
                        wins[first_name] += 1
                    elif res.winner == "B":
                        wins[second_name] += 1
                    # tie não contabiliza

    win_rate = {m: round(w / games, 3) if games else 0.0 for m, w in wins.items()}
    return {"games_played": games, "wins": wins, "win_rate": win_rate}
