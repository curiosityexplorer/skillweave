"""
Organizational Skill Governance (OSG) — Section VII of the paper.

Implements:
  - Principal hierarchy integration (VII.A)
  - Data boundary enforcement
  - Regulatory compliance modules (VII.B)
  - Audit trail architecture (VII.C)
"""

from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import (
    Agent, AgentSkill, AuthorityLevel, CompositionPlan, CompositionType,
    DataBoundary, DataBoundaryType, OrganizationalPrincipal, Policy,
    PolicyAction, PolicyType, PolicyViolation, SemanticAnnotation,
    ViolationType,
)


# ─── Principal Hierarchy ─────────────────────────────────────────────────────

class PrincipalHierarchy:
    """
    Manages the organizational principal lattice (Section VII.A).
    Provides authority scoping, LUB computation, and inheritance.
    """

    def __init__(self):
        self.principals: Dict[str, OrganizationalPrincipal] = {}
        self.children: Dict[str, List[str]] = {}  # parent_id -> [child_ids]

    def add_principal(self, principal: OrganizationalPrincipal):
        self.principals[principal.id] = principal
        if principal.parent_id:
            self.children.setdefault(principal.parent_id, []).append(principal.id)

    def get_principal(self, principal_id: str) -> Optional[OrganizationalPrincipal]:
        return self.principals.get(principal_id)

    def get_ancestor_chain(self, principal_id: str) -> List[OrganizationalPrincipal]:
        """Get the chain of principals from the given principal to the root."""
        chain = []
        current_id = principal_id
        while current_id and current_id in self.principals:
            p = self.principals[current_id]
            chain.append(p)
            current_id = p.parent_id
        return chain

    def least_upper_bound(
        self, p1_id: str, p2_id: str
    ) -> Optional[OrganizationalPrincipal]:
        """
        Compute the Least Upper Bound (LUB) principal for two principals.
        This is the lowest-authority principal that has authority over both.
        """
        chain1 = {p.id: p for p in self.get_ancestor_chain(p1_id)}
        chain2 = self.get_ancestor_chain(p2_id)

        for p in chain2:
            if p.id in chain1:
                return p

        # If no common ancestor, return the highest-authority principal
        all_principals = list(self.principals.values())
        all_principals.sort(key=lambda p: p.authority.value, reverse=True)
        return all_principals[0] if all_principals else None

    def check_authority_for_composition(
        self, requesting_principal_id: str,
        skill_1: AgentSkill, skill_2: AgentSkill
    ) -> Tuple[bool, Optional[str]]:
        """
        Authority Scoping: verify that the requesting principal has sufficient
        authority for the composition. Returns (authorized, reason_if_denied).
        """
        principal = self.get_principal(requesting_principal_id)
        if not principal:
            return False, f"Unknown principal: {requesting_principal_id}"

        required_level = max(
            skill_1.min_authority_level.value,
            skill_2.min_authority_level.value
        )

        if principal.authority.value < required_level:
            return False, (
                f"Insufficient authority: principal '{principal.id}' has level "
                f"{principal.authority.value}, composition requires {required_level}"
            )

        return True, None


# ─── Data Boundary Enforcement ───────────────────────────────────────────────

class DataBoundaryEnforcer:
    """
    Enforces data compartment boundaries during skill composition (Section VII.A).
    """

    def __init__(self):
        # Explicit crossing authorizations: (from_boundary, to_boundary) -> authorized
        self.authorized_crossings: Dict[Tuple[str, str], bool] = {}

    def authorize_crossing(self, from_boundary: str, to_boundary: str):
        self.authorized_crossings[(from_boundary, to_boundary)] = True

    def check_boundary_crossing(
        self, skill_1: AgentSkill, skill_2: AgentSkill
    ) -> Tuple[bool, Optional[PolicyViolation]]:
        """
        Check if data can flow from skill_1's boundary to skill_2's boundary.
        Returns (allowed, violation_if_any).
        """
        b1 = skill_1.data_boundary
        b2 = skill_2.data_boundary

        # Same boundary: always allowed
        if b1.boundary_id == b2.boundary_id:
            return True, None

        # Check explicit crossing permission on the boundary
        if b1.allows_crossing_to(b2):
            return True, None

        # Check enforcer-level authorization
        if self.authorized_crossings.get((b1.boundary_id, b2.boundary_id), False):
            return True, None

        # Violation detected
        violation = PolicyViolation(
            violation_type=ViolationType.DATA_BOUNDARY,
            composition_id="",  # set by caller
            skill_ids=[skill_1.id, skill_2.id],
            description=(
                f"Unauthorized data boundary crossing: "
                f"'{b1.boundary_id}' → '{b2.boundary_id}'"
            ),
            policy_id=f"boundary:{b1.boundary_id}->{b2.boundary_id}",
            principal_id="",
        )
        return False, violation


# ─── Compliance Modules (Section VII.B) ──────────────────────────────────────

class ComplianceModule:
    """Base class for regulatory compliance modules."""

    def __init__(self, regulation_name: str):
        self.regulation_name = regulation_name

    def check_composition(
        self, skills: List[AgentSkill], principal_id: str
    ) -> List[PolicyViolation]:
        raise NotImplementedError


class HIPAAComplianceModule(ComplianceModule):
    """HIPAA compliance module for healthcare data protection."""

    def __init__(self):
        super().__init__("HIPAA")

    def check_composition(
        self, skills: List[AgentSkill], principal_id: str
    ) -> List[PolicyViolation]:
        violations = []

        # Check minimum necessary standard: PHI skills should not pass
        # data to non-healthcare skills without intermediation
        phi_skills = [s for s in skills if SemanticAnnotation.PHI in s.output_schema.annotations
                      or SemanticAnnotation.HIPAA_PROTECTED in s.output_schema.annotations]
        non_covered = [s for s in skills if SemanticAnnotation.PHI not in s.input_schema.annotations
                       and SemanticAnnotation.HIPAA_PROTECTED not in s.input_schema.annotations
                       and s.data_boundary.boundary_type != DataBoundaryType.REGULATORY]

        for phi_skill in phi_skills:
            for nc_skill in non_covered:
                # Check if they are adjacent in the chain
                skill_ids = [s.id for s in skills]
                try:
                    phi_idx = skill_ids.index(phi_skill.id)
                    nc_idx = skill_ids.index(nc_skill.id)
                    if nc_idx == phi_idx + 1:
                        violations.append(PolicyViolation(
                            violation_type=ViolationType.COMPLIANCE,
                            composition_id="",
                            skill_ids=[phi_skill.id, nc_skill.id],
                            description=(
                                f"HIPAA minimum necessary: PHI from '{phi_skill.id}' "
                                f"flows to non-covered entity '{nc_skill.id}'"
                            ),
                            policy_id="HIPAA-minimum-necessary",
                            principal_id=principal_id,
                        ))
                except ValueError:
                    continue

        return violations


class SOXComplianceModule(ComplianceModule):
    """SOX compliance module for financial reporting controls."""

    def __init__(self):
        super().__init__("SOX")

    def check_composition(
        self, skills: List[AgentSkill], principal_id: str
    ) -> List[PolicyViolation]:
        violations = []

        # SOX separation of duties: skills that create financial records
        # should not be composed with skills that approve them
        creators = [s for s in skills if "financial_creation" in s.semantic_tags]
        approvers = [s for s in skills if "financial_approval" in s.semantic_tags]

        if creators and approvers:
            # Check if same principal governs both
            creator_ids = [s.id for s in creators]
            approver_ids = [s.id for s in approvers]
            violations.append(PolicyViolation(
                violation_type=ViolationType.COMPLIANCE,
                composition_id="",
                skill_ids=creator_ids + approver_ids,
                description=(
                    f"SOX separation of duties: creation skills {creator_ids} "
                    f"and approval skills {approver_ids} in same composition"
                ),
                policy_id="SOX-separation-of-duties",
                principal_id=principal_id,
            ))

        return violations


class GDPRComplianceModule(ComplianceModule):
    """GDPR compliance module for data subject rights."""

    def __init__(self):
        super().__init__("GDPR")

    def check_composition(
        self, skills: List[AgentSkill], principal_id: str
    ) -> List[PolicyViolation]:
        violations = []

        # GDPR purpose limitation: PII data should not flow to skills
        # outside the declared purpose
        pii_skills = [s for s in skills if SemanticAnnotation.PII_CLASSIFIED in s.output_schema.annotations
                      or SemanticAnnotation.GDPR_SUBJECT in s.output_schema.annotations]

        for pii_skill in pii_skills:
            for other in skills:
                if other.id == pii_skill.id:
                    continue
                if SemanticAnnotation.PII_CLASSIFIED not in other.input_schema.annotations \
                   and SemanticAnnotation.GDPR_SUBJECT not in other.input_schema.annotations:
                    # Check if boundaries indicate cross-purpose usage
                    if other.data_boundary.boundary_id != pii_skill.data_boundary.boundary_id:
                        violations.append(PolicyViolation(
                            violation_type=ViolationType.COMPLIANCE,
                            composition_id="",
                            skill_ids=[pii_skill.id, other.id],
                            description=(
                                f"GDPR purpose limitation: PII from '{pii_skill.id}' "
                                f"crosses boundary to '{other.id}' without purpose alignment"
                            ),
                            policy_id="GDPR-purpose-limitation",
                            principal_id=principal_id,
                        ))

        return violations


# ─── Integrated Governance Engine ────────────────────────────────────────────

class OrganizationalSkillGovernance:
    """
    Main OSG engine that integrates principal hierarchy, data boundaries,
    and regulatory compliance for skill composition governance.
    """

    def __init__(self):
        self.hierarchy = PrincipalHierarchy()
        self.boundary_enforcer = DataBoundaryEnforcer()
        self.compliance_modules: List[ComplianceModule] = [
            HIPAAComplianceModule(),
            SOXComplianceModule(),
            GDPRComplianceModule(),
        ]
        self.audit_log: List[Dict[str, Any]] = []

    def evaluate_composition(
        self, skills: List[AgentSkill],
        requesting_principal_id: str,
        composition_id: str = "",
    ) -> Tuple[bool, List[PolicyViolation], float]:
        """
        Full governance evaluation of a skill composition.
        Returns (approved, violations, evaluation_time_ms).
        """
        start = time.perf_counter_ns()
        all_violations = []

        # 1. Authority scoping check
        for i in range(len(skills) - 1):
            authorized, reason = self.hierarchy.check_authority_for_composition(
                requesting_principal_id, skills[i], skills[i + 1]
            )
            if not authorized:
                all_violations.append(PolicyViolation(
                    violation_type=ViolationType.AUTHORITY_ESCALATION,
                    composition_id=composition_id,
                    skill_ids=[skills[i].id, skills[i + 1].id],
                    description=reason or "Authority check failed",
                    policy_id="authority-scoping",
                    principal_id=requesting_principal_id,
                ))

        # 2. Data boundary enforcement
        for i in range(len(skills) - 1):
            allowed, violation = self.boundary_enforcer.check_boundary_crossing(
                skills[i], skills[i + 1]
            )
            if not allowed and violation:
                violation.composition_id = composition_id
                violation.principal_id = requesting_principal_id
                all_violations.append(violation)

        # 3. Regulatory compliance
        for module in self.compliance_modules:
            violations = module.check_composition(skills, requesting_principal_id)
            for v in violations:
                v.composition_id = composition_id
            all_violations.extend(violations)

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

        # Audit log entry
        self.audit_log.append({
            "timestamp": time.time(),
            "composition_id": composition_id,
            "principal_id": requesting_principal_id,
            "skill_ids": [s.id for s in skills],
            "violations": len(all_violations),
            "approved": len(all_violations) == 0,
            "evaluation_time_ms": elapsed_ms,
        })

        return (len(all_violations) == 0, all_violations, elapsed_ms)
