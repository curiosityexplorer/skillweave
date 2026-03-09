#!/bin/bash
# SkillWeave Experimental Harness — Run all experiments
# Usage: ./run_experiments.sh [--seed 42]

set -e

SEED=${1:-42}
if [ "$1" = "--seed" ]; then
    SEED=$2
fi

echo "============================================================"
echo "SkillWeave Experimental Harness"
echo "Seed: $SEED"
echo "============================================================"

cd "$(dirname "$0")"

# Run experiments
python experiments/run_experiments.py --seed "$SEED"

echo ""
echo "============================================================"
echo "Generating paper tables..."
echo "============================================================"

python experiments/generate_tables.py

echo ""
echo "============================================================"
echo "Results saved to results/"
echo "  Raw data:       results/raw/"
echo "  Aggregated:     results/aggregated/"
echo "============================================================"
