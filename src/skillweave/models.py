"""
Core data models for the SkillWeave framework.

Implements Definition 1 (Agent Skill), Definition 2 (Skill Composition),
and Definition 3 (Organizational Principal) from the paper.
"""

from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


# ─── Type System ─────────────────────────────────────────────────────────────

class BaseType(Enum):
    """Base types in SSCA's type system (Section V.A)."""
    NUMERIC = "numeric"
    TEXTUAL = "textual"
    TEMPORAL = "temporal"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    BINARY = "binary"
    JSON_OBJECT = "json_object"
    JSON_ARRAY = "json_array"


class SemanticAnnotation(Enum):
    """Semantic annotations for data classification (Section V.A)."""
    PII_CLASSIFIED = "PII-classified"
    SOX_REGULATED = "SOX-regulated"
    HIPAA_PROTECTED = "HIPAA-protected"
    GDPR_SUBJECT = "GDPR-subject"
    CONFIDENTIAL = "confidential"
    PUBLIC = "public"
    INTERNAL = "internal"
    PHI = "protected-health-information"
    FINANCIAL_PII = "financial-PII"
    TRADE_SECRET = "trade-secret"


@dataclass(frozen=True)
class TypeSchema:
    """
    Structural type schema for skill inputs/outputs.
    Supports subtyping via the `is_subtype_of` method.
    """
    fields: Tuple[Tuple[str, BaseType], ...]
    annotations: FrozenSet[SemanticAnnotation] = frozenset()

    def field_names(self) -> Set[str]:
        return {f[0] for f in self.fields}

    def field_types(self) -> Dict[str, BaseType]:
        return {f[0]: f[1] for f in self.fields}

    def is_subtype_of(self, other: "TypeSchema") -> bool:
        """
        Structural subtyping: self ⊑ other if self has at least all fields
        of other with compatible types, and self's annotations are a superset
        of other's annotations (more restrictive is subtype of less restrictive).
        """
        other_fields = other.field_types()
        self_fields = self.field_types()
        # Width subtyping: self must have all fields of other
        for name, typ in other_fields.items():
            if name not in self_fields:
                return False
            if self_fields[name] != typ:
                # Allow numeric -> numeric coercion only
                if not (self_fields[name] == BaseType.NUMERIC and typ == BaseType.NUMERIC):
                    return False
        # Annotation subtyping: self's annotations must subsume other's
        return other.annotations.issubset(self.annotations)

    def is_compatible_with(self, other: "TypeSchema") -> Tuple[bool, List[str]]:
        """Check compatibility and return (compatible, list_of_issues)."""
        issues = []
        other_fields = other.field_types()
        self_fields = self.field_types()

        for name, typ in other_fields.items():
            if name not in self_fields:
                issues.append(f"Missing field: {name}")
            elif self_fields[name] != typ:
                issues.append(f"Type mismatch on '{name}': {self_fields[name].value} vs {typ.value}")

        annotation_diff = other.annotations - self.annotations
        if annotation_diff:
            issues.append(f"Missing annotations: {[a.value for a in annotation_diff]}")

        return (len(issues) == 0, issues)

    def compatibility_score(self, other: "TypeSchema") -> float:
        """
        Return a 0.0-1.0 compatibility score between output (self) and input (other).
        Used for runtime failure probability estimation in H4.
        1.0 = fully compatible, 0.0 = completely incompatible.
        """
        if not other.fields:
            return 1.0
        other_fields = other.field_types()
        self_fields = self.field_types()
        matched = 0
        for name, typ in other_fields.items():
            if name in self_fields and self_fields[name] == typ:
                matched += 1
            elif name in self_fields:
                matched += 0.3  # Type mismatch but field exists
        base_score = matched / len(other_fields) if other_fields else 1.0

        # Domain affinity: skills sharing semantic annotations are
        # likely from the same domain and share implicit data models
        # (e.g., patient_id in healthcare, portfolio_id in finance)
        shared_annotations = self.annotations & other.annotations
        if shared_annotations:
            affinity_bonus = min(0.45, len(shared_annotations) * 0.20)
            base_score = min(1.0, base_score + affinity_bonus)

        return base_score


# ─── Policy Model ────────────────────────────────────────────────────────────

class PolicyType(Enum):
    """Types of governance policies."""
    DATA_ACCESS = "data_access"
    DATA_RETENTION = "data_retention"
    DATA_SHARING = "data_sharing"
    EXECUTION_AUTHORITY = "execution_authority"
    AUDIT_REQUIREMENT = "audit_requirement"
    COMPLIANCE_MANDATE = "compliance_mandate"
    RATE_LIMIT = "rate_limit"


class PolicyAction(Enum):
    """Policy enforcement actions."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_AUDIT = "require_audit"
    REQUIRE_ENCRYPTION = "require_encryption"


@dataclass(frozen=True)
class Policy:
    """A governance policy constraint."""
    id: str
    policy_type: PolicyType
    action: PolicyAction
    scope: str  # e.g., "department:finance", "regulation:HIPAA"
    conditions: Tuple[str, ...] = ()
    priority: int = 0  # higher = more authoritative

    def conflicts_with(self, other: "Policy") -> bool:
        """Check if two policies have contradictory mandates."""
        if self.scope != other.scope:
            return False
        if self.policy_type != other.policy_type:
            return False
        # Direct contradictions
        contradictory_pairs = {
            (PolicyAction.ALLOW, PolicyAction.DENY),
            (PolicyAction.DENY, PolicyAction.ALLOW),
            (PolicyAction.ALLOW, PolicyAction.REQUIRE_APPROVAL),
            (PolicyAction.REQUIRE_APPROVAL, PolicyAction.ALLOW),
        }
        if (self.action, other.action) in contradictory_pairs:
            return True
        return False


# ─── Data Boundary Model ────────────────────────────────────────────────────

class DataBoundaryType(Enum):
    """Types of organizational data boundaries."""
    DEPARTMENT = "department"
    DIVISION = "division"
    REGULATORY = "regulatory"
    GEOGRAPHIC = "geographic"
    CLASSIFICATION = "classification"


@dataclass(frozen=True)
class DataBoundary:
    """Specifies the data compartment a skill operates within."""
    boundary_type: DataBoundaryType
    boundary_id: str  # e.g., "dept:clinical", "reg:HIPAA", "geo:EU"
    allowed_crossings: FrozenSet[str] = frozenset()  # boundary_ids that can be crossed

    def allows_crossing_to(self, other: "DataBoundary") -> bool:
        """Check if data can cross from this boundary to another."""
        if self.boundary_id == other.boundary_id:
            return True
        return other.boundary_id in self.allowed_crossings


# ─── Organizational Principal ────────────────────────────────────────────────

class AuthorityLevel(Enum):
    """Authority levels in the organizational principal hierarchy."""
    ENTERPRISE = 5
    DIVISION = 4
    DEPARTMENT = 3
    TEAM = 2
    INDIVIDUAL = 1


@dataclass(frozen=True)
class OrganizationalPrincipal:
    """
    Definition 3: An organizational principal π = ⟨role, authority, scope, policies⟩.
    Principals form a partial order π₁ ≤ π₂.
    """
    id: str
    role: str
    authority: AuthorityLevel
    scope: str
    policies: FrozenSet[str] = frozenset()  # policy IDs
    parent_id: Optional[str] = None

    def has_authority_over(self, other: "OrganizationalPrincipal") -> bool:
        """Check if this principal's authority subsumes another's."""
        return self.authority.value >= other.authority.value


# ─── Agent Skill ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SkillVersion:
    """Semantic versioning with policy compatibility (Section VIII.A)."""
    major: int
    minor: int
    patch: int
    policy_tag: str = ""  # e.g., "HIPAA-v2", "SOX-2024"

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.policy_tag}" if self.policy_tag else base

    def is_compatible_with(self, other: "SkillVersion") -> bool:
        """Same MAJOR.MINOR and compatible policy tags can compose without renegotiation."""
        if self.major != other.major:
            return False
        if self.minor != other.minor:
            return False
        if self.policy_tag and other.policy_tag and self.policy_tag != other.policy_tag:
            return False
        return True


@dataclass
class AgentSkill:
    """
    Definition 1: An agent skill s = ⟨id, σ_in, σ_out, P, D, v⟩.
    """
    id: str
    name: str
    description: str
    input_schema: TypeSchema
    output_schema: TypeSchema
    required_permissions: FrozenSet[str]
    policies: FrozenSet[Policy]
    data_boundary: DataBoundary
    version: SkillVersion
    semantic_tags: FrozenSet[str] = frozenset()
    min_authority_level: AuthorityLevel = AuthorityLevel.INDIVIDUAL
    quality_metrics: Dict[str, float] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, AgentSkill) and self.id == other.id


# ─── Agent ───────────────────────────────────────────────────────────────────

@dataclass
class Agent:
    """An AI agent possessing a set of skills."""
    id: str
    name: str
    domain: str  # e.g., "financial_services", "healthcare"
    skills: List[AgentSkill]
    principal: OrganizationalPrincipal
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Agent) and self.id == other.id

    @property
    def skill_ids(self) -> Set[str]:
        return {s.id for s in self.skills}

    def get_skill(self, skill_id: str) -> Optional[AgentSkill]:
        for s in self.skills:
            if s.id == skill_id:
                return s
        return None


# ─── Composition Structures ──────────────────────────────────────────────────

class CompositionType(Enum):
    """Types of skill composition operators (Section V.B)."""
    SEQUENTIAL = "sequential"       # s₁ ⟪→⟫ s₂
    PARALLEL = "parallel"           # s₁ ⟪∥⟫ s₂
    CONDITIONAL = "conditional"     # s₁ ⟪?⟫ s₂
    AGGREGATION = "aggregation"     # s₁ ⟪⊕⟫ s₂
    GUARDED = "guarded"             # s₁ ⟪π⟫ s₂


class ConflictType(Enum):
    """Types of composition conflicts (Section V.C)."""
    TYPE_CONFLICT = "type_conflict"
    SEMANTIC_CONFLICT = "semantic_conflict"
    POLICY_CONFLICT = "policy_conflict"


class ViolationType(Enum):
    """Types of policy violations (Section III.C)."""
    DATA_BOUNDARY = "data_boundary"       # T2
    AUTHORITY_ESCALATION = "authority_escalation"  # T3
    COMPLIANCE = "compliance"             # T4/regulatory


@dataclass
class CompositionConflict:
    """A detected conflict in a skill composition."""
    conflict_type: ConflictType
    skill_1_id: str
    skill_2_id: str
    description: str
    severity: float  # 0.0 to 1.0
    detection_time_ms: float = 0.0


@dataclass
class PolicyViolation:
    """A detected policy violation during composition."""
    violation_type: ViolationType
    composition_id: str
    skill_ids: List[str]
    description: str
    policy_id: str
    principal_id: str


@dataclass
class CompositionPlan:
    """
    A validated plan for composing skills across agents.
    Produced by SWOP Phase 2 (Negotiation) and formalized in Phase 3 (Contracting).
    """
    id: str
    composition_type: CompositionType
    skill_chain: List[str]  # ordered skill IDs
    agent_assignments: Dict[str, str]  # skill_id -> agent_id
    policies_applied: List[str]
    data_flow_spec: Dict[str, Any]
    conflicts_detected: List[CompositionConflict]
    violations_detected: List[PolicyViolation]
    is_valid: bool = False
    planning_time_ms: float = 0.0
    negotiation_time_ms: float = 0.0
    contracting_time_ms: float = 0.0


@dataclass
class ExecutionTrace:
    """An auditable execution trace for a composition."""
    composition_id: str
    entries: List[Dict[str, Any]] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    success: bool = False
    error: Optional[str] = None

    def add_entry(self, event_type: str, skill_id: str, data_hash: str,
                  principal_id: str, policy_evaluations: List[str], outcome: str):
        self.entries.append({
            "timestamp": time.time(),
            "event_type": event_type,
            "composition_id": self.composition_id,
            "skill_id": skill_id,
            "data_hash": data_hash,
            "principal_id": principal_id,
            "policy_evaluations": policy_evaluations,
            "outcome": outcome,
        })

    def to_json(self) -> str:
        return json.dumps({
            "composition_id": self.composition_id,
            "entries": self.entries,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "success": self.success,
            "error": self.error,
        }, indent=2)
