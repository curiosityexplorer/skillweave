# v3 evaluation (new submission after TSC-2026-03-0324.R2)

All v3 experiments are deterministic and measure the real admission judgment.
Nothing is simulated: no injected failure rates, no assumed detection
probabilities, no synthetic protocol overhead.

| Script | What it measures | Output |
|---|---|---|
| `run_threat_coverage.py` | prevalence of each violated clause and threat class over **all** ordered 2- and 3-skill chains (3 requesters each) plus the 40 expert scenarios; coverage of each mechanism class (M0–M5, SW); unsafe compositions admitted per mechanism; static-vs-monitor consistency on every evaluation; audit-chain verification; inline latency | `results_v3/aggregated/threat_coverage.json`, `results_v3/raw/*.csv` |
| `run_scalability_v3.py` | judgment latency vs. chain length (2–47) and exhaustive pairwise admission vs. registry size (47–752) | `results_v3/aggregated/scalability_v3.json` |
| `run_llm_planner_paired.py` | LLM-planned chains through the gate, **paired** design, chains logged, all mechanisms evaluated on the same proposals; `--client scripted` is a wiring check only | `results_v3/aggregated/llm_planner_paired_<client>.json` |

The judgment itself lives in `src/skillweave/judgment.py` (footprints, clauses
V1–V6, mechanism ladder, runtime monitor, hash-chained audit log).  The
mutual-exclusion constraints used by the testbed are declared at the top of
`run_threat_coverage.py`.

## Superseded

`run_experiments.py` (H1–H4) and `run_autogen_integration.py` are retained for
the record but their outputs must **not** be reported as measurements:

* H2 (`Table II` overhead) adds Gaussian "calibrated overhead" to each phase;
* H3 (`Table III` violation rates) decides whether B2 catches a violation by a
  random draw and fixes B3/SkillWeave detection by assumption;
* H4 (`Table IV` success rates) is a parameterised simulation;
* `run_autogen_integration.py` does not use the AutoGen runtime, draws
  proposals independently per configuration, does not log chains, and
  simulates execution with an injected failure rate.

Use the v3 scripts instead.

## Reproduce (seed 42; ~1 minute on 2 vCPU)

```bash
python experiments/run_threat_coverage.py --out results_v3
python experiments/run_scalability_v3.py --out results_v3
# optional, needs OPENAI_API_KEY (≈ 40 short completions):
python experiments/run_llm_planner_paired.py --client openai --model gpt-4o-mini --seed 42 --out results_v3
```
