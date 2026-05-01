"""
Cost tracker — telemetria por chamada de LLM.

Registra `{provider, model, in_tokens, out_tokens, cost_usd, latency_ms,
schema_failure}` para cada `complete()` que passa por algum LLMProvider.

Uso:
    from cfai.cost_tracker import cost_tracker, estimate_cost
    cost_tracker.record(provider="openai", model="gpt-4o",
                        in_tokens=500, out_tokens=200, latency_ms=1234)
    print(cost_tracker.report())

Pricing dict abaixo são aproximações (USD por 1M tokens). Para o paper
final, validar contra invoices reais.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# (input_$/M, output_$/M) — aproximado, atualizar conforme docs oficiais.
# Marcado [E] = estimate quando não há preço público claro pra essa variante.
PRICING: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-sonnet-4-6":     (3.00, 15.00),
    "claude-opus-4-7":       (15.00, 75.00),
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    # OpenAI
    "gpt-5":                 (1.25, 10.00),
    "gpt-5-mini":            (0.25, 2.00),
    "gpt-4o":                (2.50, 10.00),
    "gpt-4o-mini":           (0.15, 0.60),
    # DeepSeek
    "deepseek-chat":         (0.27, 1.10),
    "deepseek-v4-flash":     (0.10, 0.30),    # [E] flash variant
    # Groq (hospeda OSS)
    "qwen/qwen3-32b":        (0.29, 0.59),
    "llama-3.3-70b-versatile": (0.59, 0.79),
    # Minimax
    "MiniMax-M2":            (0.20, 1.10),
    "MiniMax-M2.7":          (0.20, 1.10),    # [E] usando M2 como proxy
    "abab6.5s-chat":         (0.30, 1.50),
}


def estimate_cost(model: str, in_tokens: int, out_tokens: int) -> float:
    """Custo USD estimado. Fallback para 0.0 se modelo desconhecido."""
    prices = PRICING.get(model)
    if not prices:
        return 0.0
    in_price, out_price = prices
    return (in_tokens / 1_000_000) * in_price + (out_tokens / 1_000_000) * out_price


@dataclass
class CallRecord:
    timestamp: datetime
    provider: str
    model: str
    in_tokens: int
    out_tokens: int
    cost_usd: float
    latency_ms: int
    schema_failure: bool = False
    label: Optional[str] = None  # opcional: "smoke_test", "judge_pointwise", etc


@dataclass
class CostTracker:
    """Singleton-ish — usar via `cost_tracker` global abaixo."""
    records: list[CallRecord] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record(
        self, *,
        provider: str, model: str,
        in_tokens: int, out_tokens: int,
        latency_ms: int,
        schema_failure: bool = False,
        label: Optional[str] = None,
    ) -> CallRecord:
        cost = estimate_cost(model, in_tokens, out_tokens)
        rec = CallRecord(
            timestamp=datetime.now(),
            provider=provider, model=model,
            in_tokens=in_tokens, out_tokens=out_tokens,
            cost_usd=cost, latency_ms=latency_ms,
            schema_failure=schema_failure, label=label,
        )
        with self._lock:
            self.records.append(rec)
        return rec

    def reset(self) -> None:
        with self._lock:
            self.records.clear()

    def report(self) -> dict:
        """Resumo agregado por provider + total."""
        with self._lock:
            recs = list(self.records)
        if not recs:
            return {"n_calls": 0, "total_cost_usd": 0.0, "by_provider": {}}

        by_provider: dict[str, dict] = {}
        for r in recs:
            b = by_provider.setdefault(r.provider, {
                "n_calls": 0, "in_tokens": 0, "out_tokens": 0,
                "cost_usd": 0.0, "latency_ms_total": 0,
                "schema_failures": 0, "models": set(),
            })
            b["n_calls"] += 1
            b["in_tokens"] += r.in_tokens
            b["out_tokens"] += r.out_tokens
            b["cost_usd"] += r.cost_usd
            b["latency_ms_total"] += r.latency_ms
            b["schema_failures"] += int(r.schema_failure)
            b["models"].add(r.model)

        for b in by_provider.values():
            b["latency_ms_avg"] = round(b["latency_ms_total"] / b["n_calls"])
            b["schema_failure_rate"] = round(b["schema_failures"] / b["n_calls"], 3)
            b["cost_usd"] = round(b["cost_usd"], 6)
            b["models"] = sorted(b["models"])
            del b["latency_ms_total"]

        return {
            "n_calls": len(recs),
            "total_cost_usd": round(sum(r.cost_usd for r in recs), 6),
            "total_in_tokens": sum(r.in_tokens for r in recs),
            "total_out_tokens": sum(r.out_tokens for r in recs),
            "by_provider": by_provider,
        }


# Singleton global. Importar como `from cfai.cost_tracker import cost_tracker`.
cost_tracker = CostTracker()
