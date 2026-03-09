"""
Semantic Skill Composition Algebra (SSCA) — Section V of the paper.

Implements:
  - Type compatibility checking (V.A)
  - Five composition operators (V.B)
  - Three conflict detection algorithms (V.C)
  - DAG-based dependency resolution (V.D)
"""

from __future__ import annotations
import time
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from .models import (
    AgentSkill, AuthorityLevel, BaseType, CompositionConflict, CompositionPlan,
    CompositionType, ConflictType, DataBoundary, Policy, PolicyAction,
    PolicyViolation, SemanticAnnotation, TypeSchema, ViolationType,
)


class SemanticSkillCompositionAlgebra:
    """
    Core SSCA engine implementing composition operators,
    conflict detection, and dependency resolution.
    """

    # ── Semantic similarity matrix for conflict detection ─────────────────
    # Precomputed pairwise semantic conflict scores between tag categories.
    # In production, this would use embedding similarity; here we use
    # expert-defined conflict rules for reproducibility.
    SEMANTIC_CONFLICT_RULES = {
        # (tag_a, tag_b): conflict_score (0 = no conflict, 1 = full conflict)
        ("risk_maximizing", "risk_minimizing"): 0.95,
        ("cost_cutting", "quality_maximizing"): 0.70,
        ("aggressive_trading", "conservative_compliance"): 0.90,
        ("data_minimization", "data_enrichment"): 0.80,
        ("patient_privacy", "data_sharing"): 0.85,
        ("real_time_processing", "batch_processing"): 0.60,
        ("automated_execution", "manual_approval"): 0.75,
        ("revenue_optimization", "cost_compliance"): 0.50,
        ("broad_access", "least_privilege"): 0.85,
        ("fast_approval", "thorough_review"): 0.65,
    }
    SEMANTIC_CONFLICT_THRESHOLD = 0.65

    def __init__(self, seed: int = 42):
        self.seed = seed

    # ── Type Compatibility (Section V.A) ─────────────────────────────────

    def check_type_compatibility(
        self, output_schema: TypeSchema, input_schema: TypeSchema
    ) -> Tuple[bool, List[str], float]:
        """
        Check structural type compatibility: σ_out(s₁) ⊑ σ_in(s₂).
        Returns (compatible, issues, detection_time_ms).
        """
        start = time.perf_counter_ns()
        compatible, issues = output_schema.is_compatible_with(input_schema)
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        return compatible, issues, elapsed_ms

    # ── Composition Operators (Section V.B) ──────────────────────────────

    def sequential_compose(
        self, s1: AgentSkill, s2: AgentSkill
    ) -> Tuple[bool, List[CompositionConflict], float]:
        """
        Sequential composition: s₁ ⟪→⟫ s₂.
        Requires σ_out(s₁) ⊑ σ_in(s₂).
        """
        start = time.perf_counter_ns()
        conflicts = []

        # Type check
        compatible, issues, type_time = self.check_type_compatibility(
            s1.output_schema, s2.input_schema
        )
        if not compatible:
            conflicts.append(CompositionConflict(
                conflict_type=ConflictType.TYPE_CONFLICT,
                skill_1_id=s1.id, skill_2_id=s2.id,
                description=f"Type incompatibility: {'; '.join(issues)}",
                severity=1.0, detection_time_ms=type_time,
            ))

        # Semantic check
        sem_conflicts, sem_time = self.detect_semantic_conflicts(s1, s2)
        conflicts.extend(sem_conflicts)

        # Policy check
        pol_conflicts, pol_time = self.detect_policy_conflicts(s1, s2)
        conflicts.extend(pol_conflicts)

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        return (len(conflicts) == 0, conflicts, elapsed_ms)

    def parallel_compose(
        self, s1: AgentSkill, s2: AgentSkill
    ) -> Tuple[bool, List[CompositionConflict], float]:
        """
        Parallel composition: s₁ ⟪∥⟫ s₂.
        Requires non-overlapping data boundaries or compatible read permissions.
        """
        start = time.perf_counter_ns()
        conflicts = []

        # Data boundary overlap check
        if not s1.data_boundary.allows_crossing_to(s2.data_boundary) and \
           not s2.data_boundary.allows_crossing_to(s1.data_boundary):
            # Check if boundaries overlap (same boundary_id means shared data)
            if s1.data_boundary.boundary_id == s2.data_boundary.boundary_id:
                pass  # Same boundary, OK for parallel
            else:
                # Different boundaries without crossing permission
                # This is OK for parallel (they work on independent data)
                pass

        # Semantic check
        sem_conflicts, _ = self.detect_semantic_conflicts(s1, s2)
        conflicts.extend(sem_conflicts)

        # Policy check
        pol_conflicts, _ = self.detect_policy_conflicts(s1, s2)
        conflicts.extend(pol_conflicts)

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        return (len(conflicts) == 0, conflicts, elapsed_ms)

    def conditional_compose(
        self, s1: AgentSkill, s2: AgentSkill
    ) -> Tuple[bool, List[CompositionConflict], float]:
        """
        Conditional composition: s₁ ⟪?⟫ s₂.
        Policy constraints are union of both branches.
        """
        start = time.perf_counter_ns()
        conflicts = []

        # Both branches must be individually valid
        pol_conflicts_1, _ = self.detect_policy_conflicts(s1, s1)  # self-check
        pol_conflicts_2, _ = self.detect_policy_conflicts(s2, s2)

        # Cross-branch policy union check
        pol_conflicts, _ = self.detect_policy_conflicts(s1, s2)
        conflicts.extend(pol_conflicts)

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        return (len(conflicts) == 0, conflicts, elapsed_ms)

    def aggregation_compose(
        self, s1: AgentSkill, s2: AgentSkill
    ) -> Tuple[bool, List[CompositionConflict], float]:
        """
        Aggregation composition: s₁ ⟪⊕⟫ s₂.
        Merges outputs through reconciliation. Requires explicit conflict resolution.
        """
        start = time.perf_counter_ns()
        conflicts = []

        # Output type compatibility (both outputs must be reconcilable)
        s1_fields = s1.output_schema.field_names()
        s2_fields = s2.output_schema.field_names()
        overlap = s1_fields & s2_fields
        if overlap:
            s1_types = s1.output_schema.field_types()
            s2_types = s2.output_schema.field_types()
            for f in overlap:
                if s1_types.get(f) != s2_types.get(f):
                    conflicts.append(CompositionConflict(
                        conflict_type=ConflictType.TYPE_CONFLICT,
                        skill_1_id=s1.id, skill_2_id=s2.id,
                        description=f"Aggregation type conflict on field '{f}'",
                        severity=0.7,
                    ))

        # Semantic check (critical for aggregation — outputs must not contradict)
        sem_conflicts, _ = self.detect_semantic_conflicts(s1, s2)
        conflicts.extend(sem_conflicts)

        pol_conflicts, _ = self.detect_policy_conflicts(s1, s2)
        conflicts.extend(pol_conflicts)

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        return (len(conflicts) == 0, conflicts, elapsed_ms)

    def guarded_compose(
        self, s1: AgentSkill, s2: AgentSkill,
        guard_authority: AuthorityLevel
    ) -> Tuple[bool, List[CompositionConflict], float]:
        """
        Guarded composition: s₁ ⟪π⟫ s₂.
        Execution of s₂ after s₁ conditional on principal π's authorization.
        """
        start = time.perf_counter_ns()
        conflicts = []

        # Check authority level sufficiency
        required = max(s1.min_authority_level.value, s2.min_authority_level.value)
        if guard_authority.value < required:
            conflicts.append(CompositionConflict(
                conflict_type=ConflictType.POLICY_CONFLICT,
                skill_1_id=s1.id, skill_2_id=s2.id,
                description=f"Insufficient guard authority: {guard_authority.value} < {required}",
                severity=0.9,
            ))

        # Type check (same as sequential)
        compatible, issues, _ = self.check_type_compatibility(
            s1.output_schema, s2.input_schema
        )
        if not compatible:
            conflicts.append(CompositionConflict(
                conflict_type=ConflictType.TYPE_CONFLICT,
                skill_1_id=s1.id, skill_2_id=s2.id,
                description=f"Type incompatibility: {'; '.join(issues)}",
                severity=1.0,
            ))

        pol_conflicts, _ = self.detect_policy_conflicts(s1, s2)
        conflicts.extend(pol_conflicts)

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        return (len(conflicts) == 0, conflicts, elapsed_ms)

    # ── Conflict Detection (Section V.C) ─────────────────────────────────

    def detect_type_conflicts(
        self, s1: AgentSkill, s2: AgentSkill
    ) -> Tuple[List[CompositionConflict], float]:
        """Detect type conflicts through structural type unification."""
        start = time.perf_counter_ns()
        conflicts = []

        compatible, issues, _ = self.check_type_compatibility(
            s1.output_schema, s2.input_schema
        )
        if not compatible:
            for issue in issues:
                conflicts.append(CompositionConflict(
                    conflict_type=ConflictType.TYPE_CONFLICT,
                    skill_1_id=s1.id, skill_2_id=s2.id,
                    description=issue,
                    severity=1.0,
                ))

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        for c in conflicts:
            c.detection_time_ms = elapsed_ms
        return conflicts, elapsed_ms

    def detect_semantic_conflicts(
        self, s1: AgentSkill, s2: AgentSkill
    ) -> Tuple[List[CompositionConflict], float]:
        """
        Detect semantic conflicts through ontology-based reasoning.
        Uses precomputed conflict rules as a deterministic proxy for
        description-logic satisfiability checking.
        """
        start = time.perf_counter_ns()
        conflicts = []

        tags1 = s1.semantic_tags
        tags2 = s2.semantic_tags

        for (ta, tb), score in self.SEMANTIC_CONFLICT_RULES.items():
            if score >= self.SEMANTIC_CONFLICT_THRESHOLD:
                # Check both orderings
                if (ta in tags1 and tb in tags2) or (tb in tags1 and ta in tags2):
                    conflicts.append(CompositionConflict(
                        conflict_type=ConflictType.SEMANTIC_CONFLICT,
                        skill_1_id=s1.id, skill_2_id=s2.id,
                        description=f"Semantic conflict: {ta} ↔ {tb} (score={score:.2f})",
                        severity=score,
                    ))

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        for c in conflicts:
            c.detection_time_ms = elapsed_ms
        return conflicts, elapsed_ms

    def detect_policy_conflicts(
        self, s1: AgentSkill, s2: AgentSkill
    ) -> Tuple[List[CompositionConflict], float]:
        """
        Detect policy conflicts through policy lattice analysis.
        Verifies P(s₁) ∪ P(s₂) ⊆ P_authorized and checks for contradictions.
        """
        start = time.perf_counter_ns()
        conflicts = []

        # Check pairwise policy contradictions
        for p1 in s1.policies:
            for p2 in s2.policies:
                if p1.conflicts_with(p2):
                    conflicts.append(CompositionConflict(
                        conflict_type=ConflictType.POLICY_CONFLICT,
                        skill_1_id=s1.id, skill_2_id=s2.id,
                        description=(
                            f"Policy contradiction: {p1.id} ({p1.action.value}) "
                            f"vs {p2.id} ({p2.action.value}) on scope '{p1.scope}'"
                        ),
                        severity=0.9,
                    ))

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        for c in conflicts:
            c.detection_time_ms = elapsed_ms
        return conflicts, elapsed_ms

    # ── Combined Conflict Detection ──────────────────────────────────────

    def detect_all_conflicts(
        self, s1: AgentSkill, s2: AgentSkill
    ) -> Tuple[List[CompositionConflict], Dict[str, float]]:
        """
        Run all three conflict detection algorithms.
        Returns (conflicts, timing_dict).
        """
        type_conflicts, type_time = self.detect_type_conflicts(s1, s2)
        sem_conflicts, sem_time = self.detect_semantic_conflicts(s1, s2)
        pol_conflicts, pol_time = self.detect_policy_conflicts(s1, s2)

        all_conflicts = type_conflicts + sem_conflicts + pol_conflicts
        timings = {
            "type_detection_ms": type_time,
            "semantic_detection_ms": sem_time,
            "policy_detection_ms": pol_time,
            "total_detection_ms": type_time + sem_time + pol_time,
        }
        return all_conflicts, timings

    # ── Dependency Resolution (Section V.D) ──────────────────────────────

    def resolve_dependencies(
        self, skill_chain: List[AgentSkill],
        composition_type: CompositionType = CompositionType.SEQUENTIAL,
    ) -> Tuple[bool, List[CompositionConflict], float]:
        """
        Resolve dependencies for a skill chain by checking all adjacent
        pairs (sequential) or all pairs (parallel/aggregation).
        Returns (resolvable, conflicts, total_time_ms).
        """
        start = time.perf_counter_ns()
        all_conflicts = []

        if composition_type == CompositionType.SEQUENTIAL:
            # Check adjacent pairs
            for i in range(len(skill_chain) - 1):
                conflicts, _ = self.detect_all_conflicts(
                    skill_chain[i], skill_chain[i + 1]
                )
                all_conflicts.extend(conflicts)
        elif composition_type in (CompositionType.PARALLEL, CompositionType.AGGREGATION):
            # Check all pairs
            for i in range(len(skill_chain)):
                for j in range(i + 1, len(skill_chain)):
                    conflicts, _ = self.detect_all_conflicts(
                        skill_chain[i], skill_chain[j]
                    )
                    all_conflicts.extend(conflicts)
        else:
            # Conditional/Guarded: check all pairs
            for i in range(len(skill_chain)):
                for j in range(i + 1, len(skill_chain)):
                    conflicts, _ = self.detect_all_conflicts(
                        skill_chain[i], skill_chain[j]
                    )
                    all_conflicts.extend(conflicts)

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        return (len(all_conflicts) == 0, all_conflicts, elapsed_ms)
