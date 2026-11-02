#!/usr/bin/env python3
"""
Scalability of the governed-composition judgment (v3).

Measures directly (wall clock, no synthetic additions):
  (a) judgment latency vs. chain length, up to the full 47-skill registry;
  (b) exhaustive pairwise judgment over a registry replicated up to 16x.
Usage: python experiments/run_scalability_v3.py --out results_v3
"""
import argparse, json, random, statistics, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src")); sys.path.insert(0, str(Path(__file__).resolve().parent))
from skillweave.catalog import ALL_SKILLS, PRINCIPALS, BOUNDARIES  # noqa: E402
from skillweave.models import AgentSkill  # noqa: E402
from skillweave.judgment import Judgment, build_context  # noqa: E402
from run_threat_coverage import MUTUAL_EXCLUSION, requesters_for  # noqa: E402


def clone(s: AgentSkill, suffix: str) -> AgentSkill:
    return AgentSkill(id=f"{s.id}-{suffix}", name=s.name, description=s.description,
                      input_schema=s.input_schema, output_schema=s.output_schema,
                      required_permissions=s.required_permissions, policies=s.policies,
                      data_boundary=s.data_boundary, version=s.version,
                      semantic_tags=s.semantic_tags, min_authority_level=s.min_authority_level,
                      quality_metrics=dict(s.quality_metrics))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results_v3")
    ap.add_argument("--chain-reps", type=int, default=200)
    ap.add_argument("--registry-reps", type=int, default=3)
    args = ap.parse_args()
    rng = random.Random(42)
    J = Judgment(build_context(PRINCIPALS, BOUNDARIES, MUTUAL_EXCLUSION))
    base = list(ALL_SKILLS)

    chain_tbl = {}
    for L in (2, 4, 6, 9, 12, 16, 24, 32, 47):
        ts = []
        for _ in range(args.chain_reps):
            chain = rng.sample(base, L)
            req = requesters_for(chain)[1]
            t0 = time.perf_counter_ns()
            J.evaluate(chain, req, with_advisory=True)
            ts.append((time.perf_counter_ns() - t0) / 1e6)
        ts.sort()
        chain_tbl[L] = {"mean_ms": round(statistics.mean(ts), 4),
                        "p95_ms": round(ts[int(0.95 * len(ts)) - 1], 4)}
        print(f"chain L={L:>3}: mean {chain_tbl[L]['mean_ms']:.4f} ms  p95 {chain_tbl[L]['p95_ms']:.4f} ms")

    reg_tbl = {}
    for N in (47, 94, 188, 376, 752):
        reg = list(base)
        i = 0
        while len(reg) < N:
            reg.append(clone(base[i % len(base)], f"r{i}")); i += 1
        ts = []
        for _ in range(args.registry_reps):
            t0 = time.perf_counter_ns()
            for a in range(N):
                for b in range(a + 1, N):
                    J.evaluate([reg[a], reg[b]], "enterprise", with_advisory=True)
            ts.append((time.perf_counter_ns() - t0) / 1e6)
        pairs = N * (N - 1) // 2
        reg_tbl[N] = {"pairs": pairs, "mean_ms": round(statistics.mean(ts), 1),
                      "ms_per_pair": round(statistics.mean(ts) / pairs, 5)}
        print(f"registry N={N:>4}: {pairs:>7} pairs  {reg_tbl[N]['mean_ms']:.1f} ms  ({reg_tbl[N]['ms_per_pair']:.5f} ms/pair)")

    out = Path(args.out) / "aggregated"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "scalability_v3.json", "w") as f:
        json.dump({"chain": chain_tbl, "registry": reg_tbl,
                   "machine": "2 vCPU Intel Xeon 2.10GHz, Python 3.13"}, f, indent=2)


if __name__ == "__main__":
    main()
