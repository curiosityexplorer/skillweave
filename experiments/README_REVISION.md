# Revision Experiments (IEEE TSC Major Revision, TSC-2026-03-0324)

This directory adds two experiment harnesses introduced in revision to address
reviewer concerns. Both reuse the existing SkillWeave framework code in
`src/skillweave/` and the same `seed=42` reproducibility convention.

## 1. Scalability sweep — `run_scalability.py`

Addresses Reviewer 3 / AE: the original H2 tested chains only up to 9 skills
against a 47-skill registry; scalability for larger deployments was unsupported.

This harness measures the **actual, deterministic** SSCA computation cost
(type + semantic + policy conflict detection and exhaustive pairwise analysis)
as a function of (a) composition chain length up to the full 47-skill registry,
and (b) registry size, using synthetically replicated catalogs up to 752 skills.
It reports only directly measured wall-clock time for the framework's own
reasoning — no synthetic network/protocol overhead is added.

```bash
python experiments/run_scalability.py --seed 42
```

Outputs: `results/aggregated/scalability_chain.json`,
`results/aggregated/scalability_registry.json`, and matching raw CSVs.

Representative measured results (seed=42):
- Chain analysis scales linearly: ~0.006 ms (2 skills) to ~0.30 ms (47 skills).
- Exhaustive pairwise analysis scales quadratically at a stable ~0.0066 ms/pair:
  7.2 ms at 47 skills (1,081 pairs) up to ~1.87 s at 752 skills (282,376 pairs).

## 2. AutoGen integration — `run_autogen_integration.py`

Addresses Reviewer 1 (R1-1..R1-4), Reviewer 3 (R3-4, R3-6), and AE-1: validate
SkillWeave inside a real multi-agent framework, under realistic conditions, with
an external framework-native baseline.

SkillWeave is inserted as a **governance gate** that intercepts each proposed
cross-agent skill composition before execution and runs SSCA + OSG. Two
configurations are compared on the SAME expert-designed scenario set:

- `AUTOGEN_NATIVE` — AutoGen orchestrates with no SkillWeave governance.
- `AUTOGEN_SKILLWEAVE` — identical workload through the SkillWeave gate.

Realistic-condition switches: `--async-jitter` (asynchronous timing) and
`--failure-rate` (execution failures with one-retry recovery).

### Two modes

| Mode | Command | Produces |
|------|---------|----------|
| Scripted (no LLM, runs anywhere) | `--client scripted` | Governance-mechanism characterization; validates wiring; **not** an LLM-behavior result |
| Real LLM (needs API key) | `--client openai --model gpt-4o-mini` or `--client anthropic --model claude-...` | Headline "real multi-agent" numbers for the paper |

```bash
# wiring + governance characterization (no network):
python experiments/run_autogen_integration.py --client scripted --seed 42 \
    --scenarios 40 --async-jitter --failure-rate 0.15

# headline LLM-driven validation (requires OPENAI_API_KEY or ANTHROPIC_API_KEY):
python experiments/run_autogen_integration.py --client openai --model gpt-4o-mini \
    --seed 42 --scenarios 40 --async-jitter --failure-rate 0.15
```

Output: `results/aggregated/autogen_integration.json` + raw CSV. Both modes write
the **same schema**, so the paper tables can be populated from a real LLM run
without code changes.

### IMPORTANT (honesty note for the manuscript)

Numbers produced under `--client scripted` characterize the **governance
mechanism**, not LLM agent behavior. The headline claim in the revised paper —
"SkillWeave validated within a real LLM-driven multi-agent framework" — must be
backed by a run with `--client openai` or `--client anthropic` and a funded API
key. Until that run is executed, the manuscript's integration results remain a
placeholder. Do not report scripted-mode numbers as LLM results.

Representative scripted-mode result (seed=42, 40 expert scenarios):
- AUTOGEN_NATIVE: 85.0% execution success, 97.5% silently non-compliant.
- AUTOGEN_SKILLWEAVE: blocks 13/40 unsafe compositions, 0% compliance
  violations, ~0.054 ms mean gate latency; 27 admitted (25 repaired via SWOP).
