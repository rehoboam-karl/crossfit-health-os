# cfai

CrossFit AI programming system — schema validado, programmer plugável, framework de avaliação em 3 camadas.

## Quick start

```bash
git clone <seu-repo>
cd cfai
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Roda a suíte de demos
python tests/demo_programmer.py    # gera uma semana
python tests/demo_history.py        # feedback loop completo
python tests/eval_demo.py           # avaliação em 3 layers
```

## O que faz

1. **Schema** Pydantic completo: Mesocycle → Week → Session → Block → Movement
2. **Programmer** que gera sessões a partir de Athlete + Phase + contexto (composer plugável; default heurístico, slot pra Claude/GPT/Gemini)
3. **Avaliação** em 3 layers:
   - **L1 deterministic** — Prilepin, INOL, ACWR, Foster monotony, modal balance
   - **L2 LLM-as-Judge** — rubrica calibrada de 6 dimensões qualitativas
   - **L3 longitudinal** — compliance, PRs, overreaching, RPE-load decoupling

## Status atual

✅ Schema validado, 13 módulos, ~2.500 linhas
✅ Heurístico funcional gerando semanas/mesociclos válidos
✅ Framework de avaliação rodando end-to-end
🚧 ClaudeJudge / ClaudeComposer — stubs documentados
🚧 Test set congelado para benchmark — pendente
🚧 Calibração com coach humano — pendente

Ver [CLAUDE.md](./CLAUDE.md) para contexto técnico completo.

## Bibliografia

Ver `CLAUDE.md` seção "Bibliografia que ancora o framework" — Prilepin, Hristov INOL, Gabbett ACWR, Foster, Glassman, JMIR Scoping Review 2025, G-Eval, RubricEval, JudgeBench.
