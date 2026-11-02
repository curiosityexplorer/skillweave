#!/usr/bin/env python3
"""
Threat-driven coverage evaluation (v3 manuscript, Section "Evaluation").

Deterministic.  For every composition in the corpus and every requester, it
runs (i) the governed-composition judgment, (ii) each mechanism of the
enforcement ladder, and (iii) the runtime trace monitor, and reports:

  * prevalence of each violated clause / threat class in the corpus;
  * coverage of each threat class by each mechanism (fraction of compositions
    violating that class which the mechanism flags) and the unsafe-admission
    rate of each mechanism;
  * consistency of the static judgment with the runtime monitor (Theorem 1 and
    the exactness claim for sequential chains) on every composition;
  * directly measured judgment latency (no synthetic overhead is added).

Corpus
  pairs    : all 47*46 ordered 2-chains
  triples  : all 47*46*45 ordered 3-chains
  expert   : the 40 expert-designed scenarios with their assigned principals
Requesters for pairs/triples: the owning department of the first skill, its
division, and the enterprise root.

Usage:  python experiments/run_threat_coverage.py [--no-triples] [--out results]
"""
import argparse
import csv
import itertools
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skillweave.catalog import ALL_SKILLS, ALL_AGENTS, PRINCIPALS, BOUNDARIES  # noqa: E402
from skillweave.judgment import (  # noqa: E402
    Clause, Judgment, MECHANISMS, THREAT_OF, TraceMonitor, build_context,
    HashChainedAuditLog,
)

# Enterprise-level mutual-exclusion constraints (toxic permission pairs).
# These are testbed policy, stated in the manuscript.  None of them is
# tripped by any of the 20 expert scenarios designed as valid (asserted below).
MUTUAL_EXCLUSION = [
    ("write:trades", "write:compliance_findings"),   # trader authors compliance findings
    ("write:trades", "read:client_data"),            # trading on advisory client data
    ("write:trades", "read:audit_logs"),             # auditor executes trades
    ("write:patient_records", "write:claims"),       # record update + claim submission
    ("write:care_plans", "write:claims"),            # care planning + claim submission
    ("write:deidentified_data", "read:insurance_records"),  # re-identification risk
]

THREATS = ("T1", "T2", "T3")


def owner_of(skill_id):
    for a in ALL_AGENTS:
        if any(s.id == skill_id for s in a.skills):
            return a.principal
    raise KeyError(skill_id)


def requesters_for(chain):
    dept = owner_of(chain[0].id)
    div = PRINCIPALS[dept.parent_id]
    return [dept.id, div.id, "enterprise"]


def expert_scenarios():
    import importlib.util
    base = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("_re", str(base / "run_experiments.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    runner = mod.ExperimentRunner(seed=42, output_dir="/tmp/sw_probe_v3")
    return runner._generate_expert_scenarios()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--no-triples", action="store_true")
    ap.add_argument("--latency-reps", type=int, default=200)
    args = ap.parse_args()

    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "aggregated").mkdir(parents=True, exist_ok=True)

    ctx = build_context(PRINCIPALS, BOUNDARIES, MUTUAL_EXCLUSION)
    J = Judgment(ctx)
    skills = list(ALL_SKILLS)
    by_id = {s.id: s for s in skills}

    # ---- expert scenarios: sanity of the mutual-exclusion set ---------------
    scen = expert_scenarios()
    valid_names = {s["name"] for s in scen[:20]}  # first 20 are designed valid
    expert_rows = []
    for sc in scen:
        chain = [by_id[i] for i in sc["skill_ids"]]
        v = J.evaluate(chain, sc["principal_id"])
        expert_rows.append({
            "scenario": sc["name"], "domain": sc["domain"], "principal": sc["principal_id"],
            "chain": " > ".join(sc["skill_ids"]), "designed_valid": sc["name"] in valid_names,
            "admitted": v.admitted,
            "clauses": ";".join(sorted({c.value for c, _ in v.violations})),
            "advisory_semantic": len(v.advisories), "disagreements": v.policy_disagreements,
            "obligations": ";".join(sorted(o.value for o in v.obligations)),
        })
    for r in expert_rows:
        if r["designed_valid"] and Clause.V3_PRIVILEGE.value in r["clauses"]:
            raise SystemExit(f"mutual-exclusion set trips a designed-valid scenario: {r}")

    # ---- corpus --------------------------------------------------------------
    corpora = {"pairs": itertools.permutations(skills, 2)}
    if not args.no_triples:
        corpora["triples"] = itertools.permutations(skills, 3)

    audit = HashChainedAuditLog()
    rows = []
    # prevalence[corpus][clause] etc.
    prevalence = {c: Counter() for c in list(corpora) + ["expert"]}
    threat_prev = {c: Counter() for c in list(corpora) + ["expert"]}
    n_comp = Counter()
    n_unsafe = Counter()
    # coverage[mech][threat] = (flagged, total)
    cov_flag = {m: Counter() for m in MECHANISMS}
    cov_tot = Counter()
    clause_flag = {m: Counter() for m in MECHANISMS}   # per-clause coverage
    clause_tot = Counter()
    conflict_tot = Counter()                           # T1 conflicts (negotiation triggers)
    conflict_seen = {m: Counter() for m in MECHANISMS}
    unsafe_admitted = Counter()            # per mechanism, over unsafe compositions
    safe_blocked = Counter()               # per mechanism, over safe compositions (should be 0)
    decomposability_witness = 0            # M2 flags nothing but SW rejects
    witnesses = []
    thm1_viol = thm_exact_viol = 0
    latencies = defaultdict(list)
    by_requester_level = defaultdict(Counter)
    disagreements_total = 0
    obligations_total = Counter()

    def process(corpus_name, chain, requester):
        nonlocal decomposability_witness, thm1_viol, thm_exact_viol, disagreements_total
        v = J.evaluate(chain, requester, with_advisory=True)
        clauses = v.clauses()
        threats = {THREAT_OF[c] for c in clauses}
        n_comp[corpus_name] += 1
        if not v.admitted:
            n_unsafe[corpus_name] += 1
        for c in clauses:
            prevalence[corpus_name][c.value] += 1
        for t in threats:
            threat_prev[corpus_name][t] += 1
            cov_tot[t] += 1
        if v.advisories:
            prevalence[corpus_name]["adv-semantic"] += 1
        disagreements_total += v.policy_disagreements
        for o in v.obligations:
            obligations_total[o.value] += 1
        by_requester_level[ctx.level(requester)]["n"] += 1
        if not v.admitted:
            by_requester_level[ctx.level(requester)]["unsafe"] += 1
        for c in clauses:
            clause_tot[c.value] += 1
        has_pol = v.policy_disagreements > 0
        has_sem = bool(v.advisories)
        if has_pol:
            conflict_tot["policy-disagreement"] += 1
        if has_sem:
            conflict_tot["semantic-advisory"] += 1
        mech_flags = {}
        for m in MECHANISMS:
            fl = J.mechanism_verdict(m, chain, requester, full=v)
            mech_flags[m] = fl
            mech_threats = {THREAT_OF[c] for c in fl}
            for t in threats:
                if t in mech_threats:
                    cov_flag[m][t] += 1
            for c in fl:
                clause_flag[m][c.value] += 1
            if has_pol and m in ("M4", "SW"):
                conflict_seen[m]["policy-disagreement"] += 1
            if has_sem and m == "SW":
                conflict_seen[m]["semantic-advisory"] += 1
            if not v.admitted and not fl:
                unsafe_admitted[m] += 1
            if v.admitted and fl:
                safe_blocked[m] += 1
        if not v.admitted and not mech_flags["M2"]:
            decomposability_witness += 1
            if len(witnesses) < 12 and corpus_name != "triples":
                witnesses.append((requester, [s.id for s in chain], sorted(c.value for c in clauses)))
        # runtime monitor consistency
        mon = TraceMonitor(ctx, requester)
        accepted = mon.run(chain)
        static_runtime_clauses = clauses - {Clause.V1_TYPE, Clause.V5_POLICY}
        if v.admitted and not accepted:
            thm1_viol += 1
        if (not static_runtime_clauses) != accepted:
            thm_exact_viol += 1
        latencies[len(chain)].append(v.latency_ms)
        audit.append("ADMIT" if v.admitted else "BLOCK", f"{corpus_name}", [s.id for s in chain],
                     requester, "ok" if v.admitted else ";".join(sorted(c.value for c in clauses)))
        if corpus_name != "triples":
            rows.append({
                "corpus": corpus_name, "requester": requester,
                "chain": ">".join(s.id for s in chain), "admitted": v.admitted,
                "clauses": ";".join(sorted(c.value for c in clauses)),
                "advisory": len(v.advisories), "latency_ms": round(v.latency_ms, 5),
                **{f"flag_{m}": ";".join(sorted(c.value for c in mech_flags[m])) for m in MECHANISMS},
            })

    t_start = time.time()
    for name, it in corpora.items():
        for chain in it:
            for r in requesters_for(chain):
                process(name, list(chain), r)
        print(f"[coverage] {name}: {n_comp[name]} evaluations, {n_unsafe[name]} unsafe")
    for sc in scen:
        process("expert", [by_id[i] for i in sc["skill_ids"]], sc["principal_id"])
    print(f"[coverage] expert: {n_comp['expert']} evaluations, {n_unsafe['expert']} unsafe")
    print(f"[coverage] wall time {time.time()-t_start:.1f}s; audit chain verified={audit.verify()}")

    # ---- latency micro-benchmark (repeated, sampled chains 2..9) -------------
    import random
    rng = random.Random(42)
    bench = {}
    for L in (2, 3, 4, 6, 9):
        times = []
        for _ in range(args.latency_reps):
            chain = rng.sample(skills, L)
            req = requesters_for(chain)[1]
            t0 = time.perf_counter_ns()
            J.evaluate(chain, req, with_advisory=True)
            times.append((time.perf_counter_ns() - t0) / 1e6)
        times.sort()
        bench[L] = {"mean_ms": round(statistics.mean(times), 4),
                    "p95_ms": round(times[int(0.95 * len(times)) - 1], 4),
                    "max_ms": round(times[-1], 4), "reps": len(times)}

    # ---- aggregate -----------------------------------------------------------
    total_evals = sum(n_comp.values())
    agg = {
        "corpus_sizes": dict(n_comp),
        "unsafe_counts": dict(n_unsafe),
        "prevalence_by_clause": {k: dict(v) for k, v in prevalence.items()},
        "prevalence_by_threat": {k: dict(v) for k, v in threat_prev.items()},
        "coverage": {m: {t: {"flagged": cov_flag[m][t], "total": cov_tot[t],
                              "rate": round(cov_flag[m][t] / cov_tot[t], 4) if cov_tot[t] else None}
                         for t in THREATS} for m in MECHANISMS},
        "coverage_by_clause": {m: {c: {"flagged": clause_flag[m][c], "total": clause_tot[c],
                                        "rate": round(clause_flag[m][c] / clause_tot[c], 4)}
                                    for c in sorted(clause_tot)} for m in MECHANISMS},
        "conflicts_T1": {"totals": dict(conflict_tot),
                         "seen_by": {m: dict(conflict_seen[m]) for m in MECHANISMS}},
        "unsafe_admitted": {m: {"count": unsafe_admitted[m],
                                "rate_over_unsafe": round(unsafe_admitted[m] / max(1, sum(n_unsafe.values())), 4)}
                            for m in MECHANISMS},
        "safe_blocked": {m: safe_blocked[m] for m in MECHANISMS},
        "decomposability_witnesses": {"count": decomposability_witness,
                                      "examples": witnesses},
        "theorem_checks": {"admitted_but_monitor_rejected": thm1_viol,
                           "static_vs_monitor_mismatch": thm_exact_viol,
                           "evaluations": total_evals},
        "policy_disagreements_total": disagreements_total,
        "obligations_total": dict(obligations_total),
        "by_requester_level": {k: dict(v) for k, v in sorted(by_requester_level.items())},
        "latency_inline_by_chain_len": {L: {"mean_ms": round(statistics.mean(v), 4),
                                            "p95_ms": round(sorted(v)[int(0.95 * len(v)) - 1], 4),
                                            "n": len(v)} for L, v in sorted(latencies.items())},
        "latency_bench": bench,
        "mutual_exclusion": MUTUAL_EXCLUSION,
        "audit_chain_verified": audit.verify(),
        "audit_entries": len(audit.entries),
    }
    with open(out / "aggregated" / "threat_coverage.json", "w") as f:
        json.dump(agg, f, indent=2)
    with open(out / "raw" / "threat_coverage_pairs_expert_raw.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with open(out / "raw" / "expert_scenarios_v3.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(expert_rows[0].keys()))
        w.writeheader(); w.writerows(expert_rows)
    print(json.dumps({k: agg[k] for k in ("corpus_sizes", "unsafe_counts", "prevalence_by_threat",
                                          "unsafe_admitted", "theorem_checks",
                                          "decomposability_witnesses", "latency_bench")}, indent=1))


if __name__ == "__main__":
    main()
