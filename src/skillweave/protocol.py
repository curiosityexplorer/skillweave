"""
SkillWeave Orchestration Protocol (SWOP) — Section VI of the paper.

Implements the four-phase protocol:
  - Phase 1: Skill Discovery and Advertisement (VI.B)
  - Phase 2: Composition Negotiation (VI.C)
  - Phase 3: Governed Execution Contracts (VI.D)
  - Phase 4: Governed Execution (VI.E)
"""

from __future__ import annotations
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import (
    Agent, AgentSkill, CompositionPlan, CompositionType, ExecutionTrace,
    PolicyViolation, ViolationType,
)
from .algebra import SemanticSkillCompositionAlgebra
from .governance import OrganizationalSkillGovernance
from .registry import EnterpriseSkillRegistry


@dataclass
class SkillManifest:
    """
    A machine-readable document advertising an agent's skills (Section VI.B).
    Extends A2A Agent Cards with composition-relevant metadata.
    """
    agent_id: str
    skills: List[Dict[str, Any]]
    governance: Dict[str, Any]
    published_at: float = field(default_factory=time.time)

    @classmethod
    def from_agent(cls, agent: Agent) -> "SkillManifest":
        skills = []
        for s in agent.skills:
            skills.append({
                "skill_id": s.id,
                "name": s.name,
                "input_fields": list(s.input_schema.field_names()),
                "output_fields": list(s.output_schema.field_names()),
                "semantic_tags": list(s.semantic_tags),
                "version": str(s.version),
                "min_authority": s.min_authority_level.value,
                "boundary": s.data_boundary.boundary_id,
            })
        return cls(
            agent_id=agent.id,
            skills=skills,
            governance={
                "principal_id": agent.principal.id,
                "authority_level": agent.principal.authority.value,
                "scope": agent.principal.scope,
            },
        )


@dataclass
class CompositionProposal:
    """A proposal from an orchestrator to compose skills (Phase 2)."""
    proposal_id: str
    orchestrator_agent_id: str
    requested_skills: List[str]
    composition_type: CompositionType
    quality_constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NegotiationResponse:
    """A response from a candidate agent to a composition proposal."""
    agent_id: str
    proposal_id: str
    accepted: bool
    offered_skills: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    rejection_reason: Optional[str] = None


@dataclass
class GovernedExecutionContract:
    """
    A binding agreement between agents for skill composition (Phase 3).
    """
    contract_id: str
    composition_plan: CompositionPlan
    participating_agents: List[str]
    skill_chain_pinned: List[Tuple[str, str]]  # (skill_id, version)
    data_flow_spec: Dict[str, Any]
    policy_obligations: Dict[str, List[str]]  # agent_id -> [policy_ids]
    qos_guarantees: Dict[str, Any]
    signed_by: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class SkillWeaveOrchestrationProtocol:
    """
    Main SWOP engine coordinating discovery, negotiation,
    contracting, and governed execution.
    """

    def __init__(
        self,
        algebra: SemanticSkillCompositionAlgebra,
        governance: OrganizationalSkillGovernance,
        registry: EnterpriseSkillRegistry,
    ):
        self.algebra = algebra
        self.governance = governance
        self.registry = registry
        self.manifests: Dict[str, SkillManifest] = {}
        self.contracts: Dict[str, GovernedExecutionContract] = {}
        self.execution_traces: Dict[str, ExecutionTrace] = {}

    # ── Phase 1: Discovery ───────────────────────────────────────────────

    def publish_manifest(self, agent: Agent) -> Tuple[SkillManifest, float]:
        """Agent publishes its skill manifest for discovery."""
        start = time.perf_counter_ns()
        manifest = SkillManifest.from_agent(agent)
        self.manifests[agent.id] = manifest
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        return manifest, elapsed_ms

    def discover_skills(
        self, required_tags: Set[str], min_authority: int = 0
    ) -> Tuple[List[Tuple[str, str]], float]:
        """
        Discover skills matching required tags and authority level.
        Returns list of (agent_id, skill_id) tuples.
        """
        start = time.perf_counter_ns()
        results = []
        for agent_id, manifest in self.manifests.items():
            if manifest.governance.get("authority_level", 0) >= min_authority:
                for skill_info in manifest.skills:
                    skill_tags = set(skill_info.get("semantic_tags", []))
                    if required_tags & skill_tags:
                        results.append((agent_id, skill_info["skill_id"]))
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        return results, elapsed_ms

    # ── Phase 2: Negotiation ─────────────────────────────────────────────

    def negotiate_composition(
        self,
        agents: List[Agent],
        skill_ids: List[str],
        composition_type: CompositionType,
        requesting_principal_id: str,
    ) -> Tuple[Optional[CompositionPlan], float]:
        """
        Execute the three-round negotiation protocol.
        Returns (plan_or_none, negotiation_time_ms).
        """
        start = time.perf_counter_ns()
        composition_id = f"comp-{uuid.uuid4().hex[:12]}"

        # Resolve skills from agents
        resolved_skills: List[AgentSkill] = []
        agent_assignments: Dict[str, str] = {}
        for sid in skill_ids:
            for agent in agents:
                skill = agent.get_skill(sid)
                if skill:
                    resolved_skills.append(skill)
                    agent_assignments[sid] = agent.id
                    break

        if len(resolved_skills) != len(skill_ids):
            elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
            return None, elapsed_ms

        # Round 1: SSCA conflict detection
        resolvable, conflicts, _ = self.algebra.resolve_dependencies(
            resolved_skills, composition_type
        )

        # Round 2: Governance evaluation
        approved, violations, _ = self.governance.evaluate_composition(
            resolved_skills, requesting_principal_id, composition_id
        )

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

        plan = CompositionPlan(
            id=composition_id,
            composition_type=composition_type,
            skill_chain=skill_ids,
            agent_assignments=agent_assignments,
            policies_applied=[requesting_principal_id],
            data_flow_spec={},
            conflicts_detected=conflicts,
            violations_detected=violations,
            is_valid=resolvable and approved,
            planning_time_ms=elapsed_ms,
            negotiation_time_ms=elapsed_ms,
        )

        return plan, elapsed_ms

    # ── Phase 3: Contracting ─────────────────────────────────────────────

    def create_contract(
        self, plan: CompositionPlan, agents: List[Agent]
    ) -> Tuple[Optional[GovernedExecutionContract], float]:
        """Create a Governed Execution Contract from a validated plan."""
        start = time.perf_counter_ns()

        if not plan.is_valid:
            elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
            return None, elapsed_ms

        # Build pinned skill chain with versions
        pinned = []
        for sid in plan.skill_chain:
            skill = self.registry.get_skill(sid)
            if skill:
                pinned.append((sid, str(skill.version)))

        contract = GovernedExecutionContract(
            contract_id=f"gec-{uuid.uuid4().hex[:12]}",
            composition_plan=plan,
            participating_agents=list(set(plan.agent_assignments.values())),
            skill_chain_pinned=pinned,
            data_flow_spec=plan.data_flow_spec,
            policy_obligations={
                agent_id: plan.policies_applied
                for agent_id in set(plan.agent_assignments.values())
            },
            qos_guarantees={"max_latency_ms": 5000, "retry_count": 1},
            signed_by=list(set(plan.agent_assignments.values())),
        )

        self.contracts[contract.contract_id] = contract
        self.registry.record_composition(
            plan.id, plan.skill_chain
        )

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        plan.contracting_time_ms = elapsed_ms
        return contract, elapsed_ms

    # ── Phase 4: Governed Execution ──────────────────────────────────────

    def execute_composition(
        self, contract: GovernedExecutionContract,
        agents: List[Agent],
        simulate_failure_rate: float = 0.05,
    ) -> Tuple[ExecutionTrace, float]:
        """
        Execute a composition under the contract's governance constraints.
        In the experimental harness, skill execution is simulated.
        """
        import random
        rng = random.Random(42)

        start = time.perf_counter_ns()
        trace = ExecutionTrace(
            composition_id=contract.composition_plan.id,
            start_time=time.time(),
        )

        plan = contract.composition_plan
        success = True
        error_msg = None

        for i, (sid, ver) in enumerate(contract.skill_chain_pinned):
            # Simulate skill execution
            data_hash = hashlib.sha256(f"{sid}:{ver}:{i}".encode()).hexdigest()[:16]
            agent_id = plan.agent_assignments.get(sid, "unknown")

            # Runtime governance checkpoint
            if i > 0:
                prev_sid = contract.skill_chain_pinned[i - 1][0]
                prev_skill = self.registry.get_skill(prev_sid)
                curr_skill = self.registry.get_skill(sid)
                if prev_skill and curr_skill:
                    # Re-validate at execution time
                    allowed, violation = self.governance.boundary_enforcer.check_boundary_crossing(
                        prev_skill, curr_skill
                    )
                    if not allowed:
                        success = False
                        error_msg = f"Runtime boundary violation: {prev_sid} -> {sid}"
                        trace.add_entry("BOUNDARY_VIOLATION", sid, data_hash,
                                        agent_id, [], "BLOCKED")
                        break

            # Simulate execution (with configurable failure rate)
            if rng.random() < simulate_failure_rate:
                success = False
                error_msg = f"Runtime execution failure on skill {sid} (simulated)"
                trace.add_entry("EXECUTION_FAILURE", sid, data_hash,
                                agent_id, [], "FAILED")
                break

            trace.add_entry("SKILL_EXECUTED", sid, data_hash,
                            agent_id, plan.policies_applied, "SUCCESS")

        trace.end_time = time.time()
        trace.success = success
        trace.error = error_msg

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        self.execution_traces[plan.id] = trace
        return trace, elapsed_ms
