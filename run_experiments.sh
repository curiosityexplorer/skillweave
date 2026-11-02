#!/bin/bash
# SkillWeave v3 experiments — deterministic, nothing simulated.
# Usage: ./run_experiments.sh
set -e
cd "$(dirname "$0")"
echo "== threat coverage (exhaustive 2-/3-chain corpus + expert scenarios) =="
python experiments/run_threat_coverage.py --out results_v3
echo "== scalability (chain length, registry size) =="
python experiments/run_scalability_v3.py --out results_v3
echo "Results: results_v3/aggregated/*.json, results_v3/raw/*.csv"
echo "LLM-planner study (needs OPENAI_API_KEY): python experiments/run_llm_planner_paired.py --client openai --model gpt-4o-mini --seed 42 --out results_v3"
