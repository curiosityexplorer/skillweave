# SkillWeave: Governed Composition of Agent Skills Across Organizational Boundaries

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> **Paper**: *SkillWeave: Governed Composition of Agent Skills Across Organizational Boundaries* (submitted to IEEE Transactions on Services Computing)
> **Author**: Vivek Acharya (Independent Researcher, Dallas, TX, USA) — [vacharya@bu.edu](mailto:vacharya@bu.edu) — ORCID: [0009-0002-0860-9462](https://orcid.org/0009-0002-0860-9462)

---

## Overview

Enterprise multi-agent systems compose skills owned by different agents, departments and regulatory regimes. MCP and A2A settle how agents reach tools and each other; they do not settle whether a proposed composition may execute, under whose authority, and with which data flows. SkillWeave treats that decision as a formal **admission problem**: every skill carries a policy footprint (permissions, compartment, authority level, mandates), a composition term is typed to a footprint, and an authorization context either admits the term (with obligations) or blocks it. A runtime monitor re-validates every hop, an execution contract pins versions and obligations, and a hash-chained audit log records every decision.

### What the paper contributes

1. A characterisation of agent skills against tools, service operations and agents, and a threat model (STRIDE / NIST AI RMF) for cross-agent composition whose classes map onto the clauses of the admission judgment.
2. A formal model built from standard parts — a CSP fragment for behaviour, lattice-based compartments with authorised crossings, deny-overrides mandate combination, workflow-authorization set constraints, a truncation automaton as monitor — with proofs of soundness, exactness for sequential chains, compositionality and a decomposability characterisation.
3. This implementation and a threat-driven evaluation over every ordered 2- and 3-skill chain of the testbed (298,396 governed evaluations), comparing the judgment with reconstructions of established enforcement mechanisms.

### Where things are

| What | Where |
|---|---|
| The admission judgment (footprints, clauses V1–V6, mechanism ladder M0–M5, runtime monitor, hash-chained audit log) | `src/skillweave/judgment.py` |
| Testbed: 12 agents, 47 skills, principals, compartments, mandates | `src/skillweave/catalog.py` |
| Data models, type compatibility, advisory semantic layer, manifests/contracts, registry | `src/skillweave/{models,algebra,protocol,governance,registry}.py` |
| v3 experiments (deterministic; nothing simulated) | `experiments/run_threat_coverage.py`, `run_scalability_v3.py`, `run_llm_planner_paired.py` — see `experiments/README_V3.md` |
| v3 results (aggregated JSON + raw CSV) | `results_v3/` |
| Superseded harnesses and their outputs (kept for the record; **not** to be reported) | `experiments/run_experiments.py`, `run_autogen_integration.py`, `results/` |

---

## Repository Structure

```
skillweave/
├── src/skillweave/          # Core framework
│   ├── __init__.py
│   ├── models.py            # Data models (Skill, Agent, Policy, Principal)
│   ├── judgment.py          # v3: footprints, judgment V1–V6, mechanism ladder, monitor, audit chain
│   ├── algebra.py           # type compatibility + advisory semantic layer
│   ├── governance.py        # principal hierarchy, boundary enforcer, regulatory modules
│   ├── registry.py          # registry (manifests, versions, provenance counters)
│   ├── protocol.py          # manifests, contracts, hop re-validation
│   └── catalog.py           # 47 skills, 12 agents, 2 domains
├── experiments/
│   ├── README_V3.md               # v3 experiment guide (read this first)
│   ├── run_threat_coverage.py     # v3: exhaustive corpus, coverage, consistency, latency
│   ├── run_scalability_v3.py      # v3: chain-length and registry-size sweeps
│   ├── run_llm_planner_paired.py  # v3: LLM-planned chains, paired design, chains logged
│   ├── run_experiments.py         # superseded (H1–H4)
│   ├── run_autogen_integration.py # superseded
│   └── generate_tables.py         # superseded
├── results_v3/              # v3 aggregated JSON + raw CSV (what the paper reports)
├── results/                 # superseded outputs, kept for the record
├── Dockerfile               # Reproducible container
├── run_experiments.sh        # One-command execution
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.9 or higher
- No external dependencies required (pure Python)

### Reproduce the paper (v3, ~1 minute on 2 vCPU)

```bash
git clone https://github.com/curiosityexplorer/skillweave.git
cd skillweave
python experiments/run_threat_coverage.py --out results_v3     # Tables 5–7, consistency checks, inline latency
python experiments/run_scalability_v3.py --out results_v3      # Table 8
# optional, needs OPENAI_API_KEY (~40 short completions):
python experiments/run_llm_planner_paired.py --client openai --model gpt-4o-mini --seed 42 --out results_v3
```

### v3 Experiments (new submission)

The v3 evaluation (threat-driven coverage over the exhaustive 2-/3-chain corpus, measured latency, paired LLM-planner study) is in `experiments/README_V3.md`; the admission judgment is `src/skillweave/judgment.py`. The H2–H4 harnesses and `run_autogen_integration.py` below are superseded and must not be reported as measurements (see `experiments/README_V3.md`).

### Revision Experiments (IEEE TSC Major Revision, superseded)

Two additional harnesses were added during revision; see
`experiments/README_REVISION.md` for full details.

```
# Scalability sweep: SSCA reasoning cost vs. chain length and registry size
python experiments/run_scalability.py --seed 42

# Real multi-agent framework validation (AutoGen + LLM-driven agents)
#   scripted mode (no API key, validates wiring):
python experiments/run_autogen_integration.py --client scripted --seed 42 --scenarios 40
#   real LLM mode (requires OPENAI_API_KEY or ANTHROPIC_API_KEY):
python experiments/run_autogen_integration.py --client openai --model gpt-4o-mini \
    --seed 42 --scenarios 40 --async-jitter --failure-rate 0.15
```

### Docker

```bash
docker build -t skillweave .
docker run -v $(pwd)/results:/app/results skillweave
```

---

## Experimental Design (v3)

| Parameter | Value |
|-----------|-------|
| Agents / skills | 12 / 47 (24 financial services, 23 healthcare) |
| Corpus | all ordered 2-chains (2,162) and 3-chains (97,290) × 3 requesters, plus 40 expert scenarios = 298,396 governed evaluations |
| Ground truth | the formal judgment (exact for sequential chains, Theorem 2) — the evaluation measures coverage of a defined predicate, not accuracy against an external oracle |
| Mechanism ladder | M0 none · M1 static interface typing · M2 per-invocation PDP · M3 + labelled hops · M4 + policy algebra · M5 + set constraints · SW the judgment |
| Reported | prevalence per clause and threat class; coverage per mechanism; unsafe compositions admitted; static-vs-monitor consistency; audit verification; measured latency |

Nothing is simulated: no injected failures, no assumed detection rates, no synthetic protocol overhead. The earlier H1–H4 harness and the "AutoGen integration" harness are superseded; see `experiments/README_V3.md` for what they did and why their outputs are not reported.

---

## Skill Catalog

### Financial Services Agents (24 skills)

| Agent | Role | Skills |
|-------|------|--------|
| FS-Agent-1 | Portfolio Analysis | Valuation, Allocation, Attribution, Sector Exposure |
| FS-Agent-2 | Risk Assessment | VaR, Stress Testing, Counterparty Risk, Liquidity Risk |
| FS-Agent-3 | Regulatory Compliance | SOX Check, AML Screening, Report Generator, Surveillance |
| FS-Agent-4 | Trade Execution | Order Placement, Algo Trading, Pre-Trade Check, Settlement |
| FS-Agent-5 | Audit Reporting | Trail Compilation, Control Assessment, Exceptions, Dashboard |
| FS-Agent-6 | Client Advisory | Risk Profiling, Recommendations, Report Gen, Fee Calc |

### Healthcare Agents (23 skills)

| Agent | Role | Skills |
|-------|------|--------|
| HC-Agent-1 | Clinical Decision Support | Risk Stratification, Guideline Matching, Drug Interaction, Alerts |
| HC-Agent-2 | Diagnostic Analysis | Lab Interpretation, Imaging, Differential Dx, Pathology |
| HC-Agent-3 | Treatment Planning | Protocol Selection, Dosage Calc, Care Plan, Referral |
| HC-Agent-4 | Insurance Verification | Coverage, Pre-Auth, Billing Codes, Claims |
| HC-Agent-5 | HIPAA Compliance | PHI Audit, De-identification, Breach Detection, Reports |
| HC-Agent-6 | Medical Records | Retrieval, Summarization, Update |

---

## Related Work

This paper extends the governance architecture established in:

- **Governance Control Plane**: [github.com/curiosityexplorer/governance-control-plane](https://github.com/curiosityexplorer/governance-control-plane)
- **EnterpriseAgent**: [github.com/curiosityexplorer/enterprise-agent](https://github.com/curiosityexplorer/enterprise-agent)

---

## Citation

```bibtex
@article{acharya2026skillweave,
  title={SkillWeave: Governed Composition of Agent Skills Across Organizational Boundaries},
  author={Acharya, Vivek},
  journal={Submitted to IEEE Transactions on Services Computing},
  year={2026}
}
```

---
