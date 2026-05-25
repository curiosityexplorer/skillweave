"""
Scalability evaluation harness for SkillWeave (addresses Reviewer 3 / AE
scalability concerns: chains tested only up to 9 skills against a 47-skill
registry, and scalability claims for larger deployments).

This harness measures the ACTUAL, deterministic SSCA computation cost (type,
semantic, and policy conflict detection + dependency resolution) and the
pairwise-analysis cost as a function of:

  (a) composition chain length, swept up to the full registry size, and
  (b) total registry size, using synthetically replicated skill catalogs.

It reports only directly measured wall-clock time for the framework's own
reasoning. It does NOT add synthetic protocol/network overhead; any such
component is reported separately by the existing H2 harness. All runs use
seed=42 for reproducibility.

Usage:
    python experiments/run_scalability.py --seed 42
"""
import argparse
import json
import random
import statistics
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skillweave.algebra import SemanticSkillCompositionAlgebra
from skillweave.models import CompositionType, AgentSkill, SkillVersion
from skillweave.catalog import ALL_SKILLS


def clone_skill(skill: AgentSkill, suffix: str) -> AgentSkill:
    """Create a fresh skill copy with a unique id (for synthetic registry growth)."""
    return AgentSkill(
        id=f"{skill.id}-{suffix}",
        name=skill.name,
        description=skill.description,
        input_schema=skill.input_schema,
        output_schema=skill.output_schema,
        required_permissions=skill.required_permissions,
        policies=skill.policies,
        data_boundary=skill.data_boundary,
        version=skill.version,
        semantic_tags=skill.semantic_tags,
        min_authority_level=skill.min_authority_level,
        quality_metrics=dict(skill.quality_metrics),
    )


def synthetic_registry(target_size: int, rng: random.Random):
    """Replicate the real catalog up to target_size distinct skills."""
    base = list(ALL_SKILLS)
    out = list(base)
    i = 0
    while len(out) < target_size:
        src = base[i % len(base)]
        out.append(clone_skill(src, f"r{i}"))
        i += 1
    return out[:target_size]


def time_chain_analysis(ssca, chain, reps, rng):
    """Measure real SSCA sequential-composition conflict analysis for a chain."""
    times = []
    for _ in range(reps):
        start = time.perf_counter_ns()
        # Full sequential pairwise conflict analysis (type+semantic+policy)
        for a, b in zip(chain, chain[1:]):
            ssca.detect_type_conflicts(a, b)
            ssca.detect_semantic_conflicts(a, b)
            ssca.detect_policy_conflicts(a, b)
        elapsed_ms = (time.perf_counter_ns() - start) / 1e6
        times.append(elapsed_ms)
    return times


def time_pairwise_registry(ssca, skills, reps):
    """Measure real exhaustive pairwise conflict analysis over a registry."""
    times = []
    n = len(skills)
    for _ in range(reps):
        start = time.perf_counter_ns()
        for i in range(n):
            for j in range(i + 1, n):
                ssca.detect_all_conflicts(skills[i], skills[j])
        elapsed_ms = (time.perf_counter_ns() - start) / 1e6
        times.append(elapsed_ms)
    return times


def main():
    ap = argparse.ArgumentParser(description="SkillWeave scalability sweep")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-dir", type=str, default="results")
    ap.add_argument("--chain-reps", type=int, default=200)
    ap.add_argument("--registry-reps", type=int, default=5)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    ssca = SemanticSkillCompositionAlgebra(seed=args.seed)

    out_dir = Path(args.output_dir)
    raw_dir = out_dir / "raw"
    agg_dir = out_dir / "aggregated"
    raw_dir.mkdir(parents=True, exist_ok=True)
    agg_dir.mkdir(parents=True, exist_ok=True)

    print(f"[scalability] seed={args.seed}  full registry={len(ALL_SKILLS)} skills")

    # ---- Sweep A: chain length up to full registry ----
    chain_lengths = [2, 4, 6, 9, 12, 16, 24, 32, 47]
    chain_rows = []
    chain_table = {}
    for L in chain_lengths:
        # sample a chain of length L (with replacement only if L>registry)
        pool = list(ALL_SKILLS)
        if L <= len(pool):
            chain = rng.sample(pool, L)
        else:
            chain = [rng.choice(pool) for _ in range(L)]
        times = time_chain_analysis(ssca, chain, args.chain_reps, rng)
        mean = statistics.mean(times)
        chain_table[str(L)] = {
            "chain_length": L,
            "ssca_analysis_ms_mean": round(mean, 4),
            "ssca_analysis_ms_p95": round(sorted(times)[int(0.95 * len(times)) - 1], 4),
            "pairwise_checks": L - 1,
        }
        for k, t in enumerate(times):
            chain_rows.append({"chain_length": L, "rep": k, "ssca_ms": round(t, 5)})
        print(f"  chain L={L:>3}: SSCA mean={mean:.4f} ms  ({L-1} pairwise checks)")

    # ---- Sweep B: registry size (exhaustive pairwise) ----
    registry_sizes = [47, 94, 188, 376, 752]
    reg_rows = []
    reg_table = {}
    for N in registry_sizes:
        skills = synthetic_registry(N, rng)
        times = time_pairwise_registry(ssca, skills, args.registry_reps)
        mean = statistics.mean(times)
        pairs = N * (N - 1) // 2
        reg_table[str(N)] = {
            "registry_size": N,
            "pairwise_combinations": pairs,
            "exhaustive_analysis_ms_mean": round(mean, 2),
            "ms_per_pair": round(mean / pairs, 5),
        }
        for k, t in enumerate(times):
            reg_rows.append({"registry_size": N, "rep": k, "exhaustive_ms": round(t, 4)})
        print(f"  registry N={N:>4}: {pairs:>7} pairs  exhaustive mean={mean:.1f} ms  "
              f"({mean/pairs:.4f} ms/pair)")

    # ---- Save ----
    def save_csv(rows, path):
        if not rows:
            return
        keys = list(rows[0].keys())
        with open(path, "w") as f:
            f.write(",".join(keys) + "\n")
            for r in rows:
                f.write(",".join(str(r[k]) for k in keys) + "\n")

    save_csv(chain_rows, raw_dir / "scalability_chain_raw.csv")
    save_csv(reg_rows, raw_dir / "scalability_registry_raw.csv")
    with open(agg_dir / "scalability_chain.json", "w") as f:
        json.dump(chain_table, f, indent=2)
    with open(agg_dir / "scalability_registry.json", "w") as f:
        json.dump(reg_table, f, indent=2)

    print("[scalability] wrote chain + registry results to", out_dir)


if __name__ == "__main__":
    main()
