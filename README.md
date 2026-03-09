# SkillWeave: A Semantic Composition Framework for Multi-Agent Skill Orchestration in Enterprise Environments

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> **Paper**: *SkillWeave: A Semantic Composition Framework for Multi-Agent Skill Orchestration in Enterprise Environments*
> **Author**: Vivek Acharya (Boston University) — [vacharya@bu.edu](mailto:vacharya@bu.edu) — ORCID: [0009-0002-0860-9462](https://orcid.org/0009-0002-0860-9462)
> **Target Venue**: IEEE Transactions on Services Computing

---

## Overview

SkillWeave addresses a critical architectural gap in the multi-agent AI ecosystem: the absence of governed, auditable mechanisms for composing agent skills across organizational boundaries. While MCP (Model Context Protocol) standardizes agent-to-tool connectivity and A2A (Agent-to-Agent protocol) enables inter-agent communication, **no existing framework handles cross-agent skill composition** — ensuring that skills from different agents work together without conflicts, data leaks, or policy violations.

### Core Contributions

1. **Semantic Skill Composition Algebra (SSCA)** — Formal model for skill compatibility, conflict detection, and dependency resolution across multi-agent boundaries
2. **SkillWeave Orchestration Protocol (SWOP)** — Extends MCP+A2A with skill negotiation, composition planning, and governed execution contracts
3. **Organizational Skill Governance (OSG)** — Integrates principal hierarchy enforcement, data boundary compliance, and regulatory policies into the skill composition lifecycle
4. **Enterprise Skill Registry (ESR)** — Governed marketplace with skill provenance, semantic versioning, access controls, and audit trails

---

## Repository Structure

```
skillweave/
├── src/skillweave/          # Core framework
│   ├── __init__.py
│   ├── models.py            # Data models (Skill, Agent, Policy, Principal)
│   ├── algebra.py           # SSCA implementation (Section V)
│   ├── governance.py        # OSG implementation (Section VII)
│   ├── registry.py          # ESR implementation (Section VIII)
│   ├── protocol.py          # SWOP implementation (Section VI)
│   └── catalog.py           # 47 skills, 12 agents, 2 domains
├── experiments/
│   ├── run_experiments.py   # Main experimental harness (Section IX)
│   └── generate_tables.py   # Paper table generation (Tables I-IV)
├── results/
│   ├── raw/                 # Per-test raw CSV data
│   └── aggregated/          # Paper-ready JSON results
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

### Run All Experiments

```bash
# Clone the repository
git clone https://github.com/curiosityexplorer/skillweave.git
cd skillweave

# Run experiments (seed=42 for reproducibility)
python experiments/run_experiments.py --seed 42

# Generate paper tables
python experiments/generate_tables.py

# Or LaTeX format
python experiments/generate_tables.py --format latex
```

### Run Single Hypothesis

```bash
python experiments/run_experiments.py --hypothesis H1  # Conflict detection
python experiments/run_experiments.py --hypothesis H2  # Composition overhead
python experiments/run_experiments.py --hypothesis H3  # Policy violations
python experiments/run_experiments.py --hypothesis H4  # End-to-end reliability
```

### Docker

```bash
docker build -t skillweave .
docker run -v $(pwd)/results:/app/results skillweave
```

---

## Experimental Design

### Testbed Configuration

| Parameter | Value |
|-----------|-------|
| Total Agents | 12 (6 Financial Services, 6 Healthcare) |
| Total Skills | 47 (24 Financial, 23 Healthcare) |
| Pairwise Compositions | 1,081 |
| Expert Scenarios | 50 |
| Random Seed | 42 |
| Statistical Test | Welch's t-test (α = 0.05) |

### Four Hypotheses

- **H1**: SSCA accurately detects composition conflicts → Table I
- **H2**: SWOP achieves acceptable negotiation overhead → Table II
- **H3**: OSG prevents cross-boundary policy violations → Table III
- **H4**: Integrated framework enables reliable composition → Table IV

### Baseline Configurations

- **B1 (Ungoverned)**: Type-level compatibility only, no policy/semantic analysis
- **B2 (Static Policy)**: Pre-defined allow/deny rules, no dynamic negotiation
- **B3 (Agent-Local)**: Per-agent governance, no cross-agent coordination
- **SkillWeave (Full)**: Complete SSCA + SWOP + OSG + ESR

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
  title={SkillWeave: A Semantic Composition Framework for Multi-Agent
         Skill Orchestration in Enterprise Environments},
  author={Acharya, Vivek},
  journal={Submitted to IEEE Transactions on Services Computing},
  year={2026}
}
```

---
