"""
LLM provider abstraction — interface única sobre Anthropic + OpenAI-compat.

5 providers suportados: Anthropic, OpenAI, DeepSeek, Groq, Minimax.
Os 4 últimos compartilham o `openai` SDK com `base_url` parametrizado
(todos expõem chat.completions OpenAI-compatible).

Schema enforcement:
- json_mode=True faz o provider tentar retornar JSON estruturado:
  - Anthropic: instrução explícita no prompt + parser tolerante
  - OpenAI: response_format={"type": "json_object"}
  - DeepSeek/Groq/Minimax: idem (json_object — todos suportam)
- Resposta sem JSON parseável marca `schema_failure=True` no LLMResponse;
  parser tolerante tenta extrair `{...}` da string antes de falhar.

Cada `complete()` registra telemetria em `cost_tracker` (latency, tokens, $).

Faltando key da env var → ValueError no construtor; smoke test deve skipar.

Uso:
    from cfai.llm_providers import OpenAIProvider, GroqProvider
    p = OpenAIProvider()              # usa OPENAI_API_KEY do env
    resp = p.complete(system="...", user="...", json_mode=True)
    print(resp["parsed"], resp["cost_usd"])
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Optional, TypedDict

from .cost_tracker import cost_tracker


class LLMResponse(TypedDict):
    content: str                        # raw text retornado
    parsed: Optional[dict]              # JSON parseado ou None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    schema_failure: bool
    model: str
    provider: str


def _parse_json_tolerant(text: str) -> Optional[dict]:
    """Tenta json.loads direto; se falhar, busca o primeiro `{...}` no texto.
    LLMs frequentemente envolvem JSON em markdown ou comentários."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fallback: extrair primeiro objeto JSON do texto
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


# ============================================================
# Anthropic
# ============================================================

class AnthropicProvider:
    family = "anthropic"

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key: Optional[str] = None,
    ):
        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic SDK ausente. Instale: pip install anthropic"
            ) from e
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key or key.startswith("test_"):
            raise ValueError("ANTHROPIC_API_KEY ausente ou placeholder")
        self.client = anthropic.Anthropic(api_key=key)
        self.model = model
        self.name = f"anthropic-{model}"

    def complete(
        self, system: str, user: str,
        json_mode: bool = True, temperature: float = 0.0,
        max_tokens: int = 1024, label: Optional[str] = None,
    ) -> LLMResponse:
        if json_mode:
            user = (user + "\n\nIMPORTANT: Output ONLY valid JSON, no prose, "
                          "no markdown fences. Start with { and end with }.")
        t0 = time.monotonic()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        content = resp.content[0].text if resp.content else ""
        parsed = _parse_json_tolerant(content) if json_mode else None
        schema_failure = json_mode and parsed is None
        in_tok = resp.usage.input_tokens
        out_tok = resp.usage.output_tokens
        cost = cost_tracker.record(
            provider=self.family, model=self.model,
            in_tokens=in_tok, out_tokens=out_tok,
            latency_ms=latency_ms, schema_failure=schema_failure,
            label=label,
        ).cost_usd
        return LLMResponse(
            content=content, parsed=parsed,
            input_tokens=in_tok, output_tokens=out_tok,
            cost_usd=cost, latency_ms=latency_ms,
            schema_failure=schema_failure,
            model=self.model, provider=self.family,
        )


# ============================================================
# OpenAI-compatible base
# ============================================================

class OpenAICompatibleProvider:
    """Base para OpenAI/DeepSeek/Groq/Minimax. Subclasses só setam defaults."""
    family = "openai_compatible"  # subclasses sobrescrevem
    default_model = ""
    default_base_url: Optional[str] = None
    env_var = "OPENAI_API_KEY"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "openai SDK ausente. Instale: pip install openai"
            ) from e
        key = api_key or os.getenv(self.env_var)
        if not key:
            raise ValueError(f"{self.env_var} ausente no env")
        self.client = OpenAI(
            api_key=key,
            base_url=base_url or self.default_base_url,
        )
        self.model = model or self.default_model
        self.name = f"{self.family}-{self.model}"

    def complete(
        self, system: str, user: str,
        json_mode: bool = True, temperature: float = 0.0,
        max_tokens: int = 1024, label: Optional[str] = None,
    ) -> LLMResponse:
        # gpt-5 / o-series exigem max_completion_tokens; modelos antigos
        # exigem max_tokens. Tentativa optimista + fallback automático.
        token_param = (
            "max_completion_tokens"
            if self.model.startswith(("gpt-5", "o1", "o3", "o4"))
            else "max_tokens"
        )
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            token_param: max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        t0 = time.monotonic()
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            err = str(e).lower()
            # Alguns providers não aceitam json_object — retry sem
            if json_mode and "response_format" in err:
                kwargs.pop("response_format", None)
                resp = self.client.chat.completions.create(**kwargs)
            # gpt-5 / o-series não aceitam temperature != 1 (ou nem o param)
            elif "temperature" in err and "unsupported" in err:
                kwargs.pop("temperature", None)
                resp = self.client.chat.completions.create(**kwargs)
            # Fallback do max_tokens / max_completion_tokens (caso heurística falhe)
            elif "max_tokens" in err or "max_completion_tokens" in err:
                kwargs.pop("max_tokens", None)
                kwargs.pop("max_completion_tokens", None)
                alt_param = (
                    "max_tokens" if token_param == "max_completion_tokens"
                    else "max_completion_tokens"
                )
                kwargs[alt_param] = max_tokens
                resp = self.client.chat.completions.create(**kwargs)
            else:
                raise
        latency_ms = int((time.monotonic() - t0) * 1000)
        content = resp.choices[0].message.content or ""
        parsed = _parse_json_tolerant(content) if json_mode else None
        schema_failure = json_mode and parsed is None
        in_tok = resp.usage.prompt_tokens if resp.usage else 0
        out_tok = resp.usage.completion_tokens if resp.usage else 0
        cost = cost_tracker.record(
            provider=self.family, model=self.model,
            in_tokens=in_tok, out_tokens=out_tok,
            latency_ms=latency_ms, schema_failure=schema_failure,
            label=label,
        ).cost_usd
        return LLMResponse(
            content=content, parsed=parsed,
            input_tokens=in_tok, output_tokens=out_tok,
            cost_usd=cost, latency_ms=latency_ms,
            schema_failure=schema_failure,
            model=self.model, provider=self.family,
        )


# ============================================================
# Concrete OpenAI-compatible providers
# ============================================================

class OpenAIProvider(OpenAICompatibleProvider):
    family = "openai"
    default_model = "gpt-5-mini"
    env_var = "OPENAI_API_KEY"


class DeepSeekProvider(OpenAICompatibleProvider):
    family = "deepseek"
    default_model = "deepseek-v4-flash"
    default_base_url = "https://api.deepseek.com/v1"
    env_var = "DEEPSEEK_API_KEY"


class GroqProvider(OpenAICompatibleProvider):
    family = "groq"
    default_model = "qwen/qwen3-32b"
    default_base_url = "https://api.groq.com/openai/v1"
    env_var = "GROQ_API_KEY"


class MinimaxProvider(OpenAICompatibleProvider):
    family = "minimax"
    default_model = "MiniMax-M2.7"
    default_base_url = "https://api.minimax.io/v1"
    env_var = "MINIMAX_API_KEY"


# ============================================================
# Factory util
# ============================================================

PROVIDER_CLASSES: dict[str, type] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
    "groq": GroqProvider,
    "minimax": MinimaxProvider,
}


def make_provider(family: str, **kwargs):
    """Factory: `make_provider("groq")` → GroqProvider() ou raise."""
    cls = PROVIDER_CLASSES.get(family)
    if not cls:
        raise ValueError(
            f"Unknown provider {family!r}. Known: {list(PROVIDER_CLASSES)}"
        )
    return cls(**kwargs)


def available_providers() -> list[str]:
    """Quais providers têm key válida no env. Útil pra smoke tests."""
    out = []
    for name, cls in PROVIDER_CLASSES.items():
        try:
            cls()
            out.append(name)
        except (ValueError, ImportError):
            pass
    return out
