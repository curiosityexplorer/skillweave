#!/usr/bin/env python3
"""
Generate paper-ready tables from experimental results.

Usage:
  python generate_tables.py                    # Print all tables
  python generate_tables.py --format latex     # LaTeX output
  python generate_tables.py --format csv       # CSV output
"""

import argparse
import json
import sys
from pathlib import Path


def load_results(results_dir: str = "results/aggregated") -> dict:
    path = Path(results_dir) / "all_results.json"
    if not path.exists():
        print(f"ERROR: Results not found at {path}")
        print("Run experiments first: python experiments/run_experiments.py")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def print_table_i(results: dict, fmt: str = "text"):
    """Table I: Conflict Detection Performance."""
    t = results["table_i"]
    print("\n" + "=" * 70)
    print("TABLE I: Conflict Detection Performance")
    print("=" * 70)

    if fmt == "latex":
        print(r"\begin{table}[h]")
        print(r"\caption{Conflict Detection Performance}")
        print(r"\begin{tabular}{lcccc}")
        print(r"\hline")
        print(r"Conflict Type & Precision & Recall & F1-Score & Avg. Time (ms) \\")
        print(r"\hline")
        for ctype in ["type", "semantic", "policy"]:
            r = t[ctype]
            name = {"type": "Type Conflict", "semantic": "Semantic Conflict",
                    "policy": "Policy Conflict"}[ctype]
            print(f"{name} & {r['precision']:.3f} & {r['recall']:.3f} & "
                  f"{r['f1_score']:.3f} & {r['avg_detection_time_ms']:.1f} \\\\")
        print(r"\hline")
        r = t["combined"]
        print(f"Combined (Weighted) & {r['precision']:.3f} & {r['recall']:.3f} & "
              f"{r['f1_score']:.3f} & {r['avg_detection_time_ms']:.1f} \\\\")
        print(r"\hline")
        print(r"\end{tabular}")
        print(r"\end{table}")
    else:
        print(f"{'Conflict Type':<22} {'Precision':>10} {'Recall':>10} {'F1-Score':>10} {'Avg Time':>12}")
        print("-" * 70)
        for ctype in ["type", "semantic", "policy"]:
            r = t[ctype]
            name = {"type": "Type Conflict", "semantic": "Semantic Conflict",
                    "policy": "Policy Conflict"}[ctype]
            print(f"{name:<22} {r['precision']:>10.3f} {r['recall']:>10.3f} "
                  f"{r['f1_score']:>10.3f} {r['avg_detection_time_ms']:>10.1f} ms")
        print("-" * 70)
        r = t["combined"]
        print(f"{'Combined (Weighted)':<22} {r['precision']:>10.3f} {r['recall']:>10.3f} "
              f"{r['f1_score']:>10.3f} {r['avg_detection_time_ms']:>10.1f} ms")


def print_table_ii(results: dict, fmt: str = "text"):
    """Table II: Composition Overhead."""
    t = results["table_ii"]
    print("\n" + "=" * 70)
    print("TABLE II: Composition Overhead by Skill Chain Length")
    print("=" * 70)

    if fmt == "latex":
        print(r"\begin{table}[h]")
        print(r"\caption{Composition Overhead by Skill Chain Length}")
        print(r"\begin{tabular}{ccccc}")
        print(r"\hline")
        print(r"Chain Len. & Discovery (ms) & Negotiation (ms) & Contracting (ms) & Total (ms) \\")
        print(r"\hline")
        for key in sorted(t.keys(), key=lambda x: int(x)):
            r = t[key]
            print(f"{r['chain_length']} skills & {r['discovery_ms']:.1f} & "
                  f"{r['negotiation_ms']:.1f} & {r['contracting_ms']:.1f} & "
                  f"{r['total_overhead_ms']:.1f} \\\\")
        print(r"\hline")
        print(r"\end{tabular}")
        print(r"\end{table}")
    else:
        print(f"{'Chain Len.':<12} {'Discovery':>12} {'Negotiation':>14} "
              f"{'Contracting':>14} {'Total':>12}")
        print("-" * 70)
        for key in sorted(t.keys(), key=lambda x: int(x)):
            r = t[key]
            print(f"{r['chain_length']} skills{'':<6} {r['discovery_ms']:>10.1f} ms "
                  f"{r['negotiation_ms']:>12.1f} ms {r['contracting_ms']:>12.1f} ms "
                  f"{r['total_overhead_ms']:>10.1f} ms")


def print_table_iii(results: dict, fmt: str = "text"):
    """Table III: Policy Violation Rates."""
    t = results["table_iii"]
    print("\n" + "=" * 70)
    print("TABLE III: Policy Violation Rates by Configuration")
    print("=" * 70)

    if fmt == "latex":
        print(r"\begin{table}[h]")
        print(r"\caption{Policy Violation Rates by Configuration}")
        print(r"\begin{tabular}{lcccc}")
        print(r"\hline")
        print(r"Configuration & Data Boundary & Authority Esc. & Compliance & Total \\")
        print(r"\hline")
        for cname in ["B1_ungoverned", "B2_static_policy", "B3_agent_local", "SkillWeave"]:
            r = t[cname]
            label = cname.replace("_", " ")
            print(f"{label} & {r['data_boundary_pct']:.1f}\\% & "
                  f"{r['authority_escalation_pct']:.1f}\\% & "
                  f"{r['compliance_pct']:.1f}\\% & "
                  f"{r['total_violation_pct']:.1f}\\% \\\\")
        print(r"\hline")
        print(r"\end{tabular}")
        print(r"\end{table}")
    else:
        print(f"{'Configuration':<22} {'Data Bndry':>12} {'Auth Esc.':>12} "
              f"{'Compliance':>12} {'Total':>12}")
        print("-" * 70)
        for cname in ["B1_ungoverned", "B2_static_policy", "B3_agent_local", "SkillWeave"]:
            r = t[cname]
            label = cname.replace("_", " ")
            print(f"{label:<22} {r['data_boundary_pct']:>10.1f}% "
                  f"{r['authority_escalation_pct']:>10.1f}% "
                  f"{r['compliance_pct']:>10.1f}% "
                  f"{r['total_violation_pct']:>10.1f}%")


def print_table_iv(results: dict, fmt: str = "text"):
    """Table IV: Composition Success Rates."""
    t = results["table_iv"]
    print("\n" + "=" * 70)
    print("TABLE IV: Composition Success Rates by Domain")
    print("=" * 70)

    if fmt == "latex":
        print(r"\begin{table}[h]")
        print(r"\caption{Composition Success Rates by Domain}")
        print(r"\begin{tabular}{lccc}")
        print(r"\hline")
        print(r"Configuration & Financial Svcs. & Healthcare & Overall \\")
        print(r"\hline")
        for cname in ["B1_ungoverned", "B2_static_policy", "B3_agent_local", "SkillWeave"]:
            r = t[cname]
            label = cname.replace("_", " ")
            print(f"{label} & {r['financial_services_pct']:.1f}\\% & "
                  f"{r['healthcare_pct']:.1f}\\% & "
                  f"{r['overall_pct']:.1f}\\% \\\\")
        print(r"\hline")
        print(r"\end{tabular}")
        print(r"\end{table}")
    else:
        print(f"{'Configuration':<22} {'Financial':>14} {'Healthcare':>14} {'Overall':>12}")
        print("-" * 70)
        for cname in ["B1_ungoverned", "B2_static_policy", "B3_agent_local", "SkillWeave"]:
            r = t[cname]
            label = cname.replace("_", " ")
            print(f"{label:<22} {r['financial_services_pct']:>12.1f}% "
                  f"{r['healthcare_pct']:>12.1f}% "
                  f"{r['overall_pct']:>12.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Generate paper tables from results")
    parser.add_argument("--format", choices=["text", "latex", "csv"], default="text")
    parser.add_argument("--results-dir", default="results/aggregated")
    args = parser.parse_args()

    results = load_results(args.results_dir)
    print_table_i(results, args.format)
    print_table_ii(results, args.format)
    print_table_iii(results, args.format)
    print_table_iv(results, args.format)


if __name__ == "__main__":
    main()
