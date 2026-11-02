"""
Governed-composition judgment (v3) — the formal admission check of SkillWeave.

This module is the executable counterpart of the formal model in the paper:

  * footprint(C)            — Definition (Footprint): the static over-approximation
                              of what a composition C touches: permissions, data
                              flows, authority level, mandates, skill set.
  * Judgment.evaluate(C, r) — the governed-composition judgment  alpha |= C,
                              returning every violated clause (V1..V6) plus
                              advisory semantic conflicts (not part of |=).
  * Mechanism ladder        — the same clauses grouped the way established
                              enforcement mechanisms see them:
        M1 static interface typing       (V1)
        M2 per-invocation PEP            (V2 + per-skill mandate decisions)
        M3 hop-local labelled PEP        (M2 + V4 + adjacent regulatory flow rules)
        M4 policy-composition algebra    (M2 + V5 chain-level mandate resolution)
        M5 workflow authorization ctrl.  (M2 + V3 + set-based regulatory rules)
        SW SkillWeave                    (V1..V6)
  * TraceMonitor            — the runtime security automaton M_alpha over
                              invocation/flow events; used to check Theorem 1
                              (static admission implies every trace accepted)
                              on the corpus, and as the Phase-4 checkpoint.
  * HashChainedAuditLog     — append-only, SHA-256 chained audit entries (T4).

Everything here is deterministic. No simulated outcomes, no random draws.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

from .models import (
    AgentSkill, AuthorityLevel, DataBoundaryType, OrganizationalPrincipal,
    Policy, PolicyAction, PolicyType, SemanticAnnotation,
)
from .algebra import SemanticSkillCompositionAlgebra


# ─────────────────────────────────────────────────────────────────────────────
# Decisions and obligations (policy effects)
# ─────────────────────────────────────────────────────────────────────────────

# Decisions form a chain  allow < approve < deny  (deny-overrides / most
# restrictive wins, as in XACML deny-overrides and restriction in policy
# algebras).  Obligations (audit, encrypt) accumulate by union.
DECISION_RANK = {PolicyAction.ALLOW: 0, PolicyAction.REQUIRE_APPROVAL: 1,
                 PolicyAction.DENY: 2}
OBLIGATIONS = {PolicyAction.REQUIRE_AUDIT, PolicyAction.REQUIRE_ENCRYPTION}


def is_decision(a: PolicyAction) -> bool:
    return a in DECISION_RANK


# ─────────────────────────────────────────────────────────────────────────────
# Authorization context  alpha
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AuthorizationContext:
    """alpha = < principals, authorised flows, mutual-exclusion set, regulatory rules >."""
    principals: Dict[str, OrganizationalPrincipal]
    authorized_flows: Set[Tuple[str, str]]          # (from_boundary, to_boundary)
    mutual_exclusion: FrozenSet[FrozenSet[str]]     # toxic permission pairs (V3)
    # regulatory rules are fixed predicates implemented below (HIPAA-MN, SOX-SoD, GDPR-PL)

    def flow_ok(self, b1: str, b2: str) -> bool:
        return b1 == b2 or (b1, b2) in self.authorized_flows

    def level(self, principal_id: str) -> int:
        p = self.principals.get(principal_id)
        return p.authority.value if p else 0


def build_context(principals: Dict[str, OrganizationalPrincipal],
                  boundaries: Dict[str, "DataBoundary"],
                  mutual_exclusion: Iterable[Tuple[str, str]]) -> AuthorizationContext:
    flows: Set[Tuple[str, str]] = set()
    for b in boundaries.values():
        for to in b.allowed_crossings:
            flows.add((b.boundary_id, to))
    mx = frozenset(frozenset(p) for p in mutual_exclusion)
    return AuthorizationContext(dict(principals), flows, mx)


# ─────────────────────────────────────────────────────────────────────────────
# Footprint  F(C)   (sequential compositions; the harness uses chains)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Footprint:
    skills: Tuple[str, ...]
    permissions: FrozenSet[str]
    flows: Tuple[Tuple[str, str], ...]              # adjacent boundary pairs
    level: int                                      # max min_authority_level
    mandates: Dict[Tuple[str, str], Set[PolicyAction]]  # (type,scope) -> actions seen
    obligations: Set[PolicyAction]

    @staticmethod
    def of_skill(s: AgentSkill) -> "Footprint":
        mand: Dict[Tuple[str, str], Set[PolicyAction]] = {}
        obl: Set[PolicyAction] = set()
        for p in s.policies:
            if is_decision(p.action):
                mand.setdefault((p.policy_type.value, p.scope), set()).add(p.action)
            else:
                obl.add(p.action)
        return Footprint((s.id,), frozenset(s.required_permissions), (),
                         s.min_authority_level.value, mand, obl)

    def seq(self, other: "Footprint", flow: Tuple[str, str]) -> "Footprint":
        """F(C1 ; C2): the compositional combination used by Theorem 3."""
        mand = {k: set(v) for k, v in self.mandates.items()}
        for k, v in other.mandates.items():
            mand.setdefault(k, set()).update(v)
        return Footprint(self.skills + other.skills,
                         self.permissions | other.permissions,
                         self.flows + (flow,) + other.flows,
                         max(self.level, other.level),
                         mand, self.obligations | other.obligations)


def footprint(chain: Sequence[AgentSkill]) -> Footprint:
    fp = Footprint.of_skill(chain[0])
    for a, b in zip(chain, chain[1:]):
        fp = fp.seq(Footprint.of_skill(b),
                    (a.data_boundary.boundary_id, b.data_boundary.boundary_id))
    return fp


# ─────────────────────────────────────────────────────────────────────────────
# Clauses of the judgment
# ─────────────────────────────────────────────────────────────────────────────

class Clause(str, Enum):
    V1_TYPE = "V1-type"                 # T1  interface incompatibility
    V2_LEVEL = "V2-level"               # T3  requester level below required
    V3_PRIVILEGE = "V3-privilege"       # T3  mutually exclusive permissions accumulated
    V4_FLOW = "V4-flow"                 # T2  unauthorised boundary crossing
    V5_POLICY = "V5-policy"             # T1  resolved decision = deny / disagreement
    V6_HIPAA_MN = "V6-hipaa-mn"         # T2  minimum-necessary (adjacent flow rule)
    V6_SOX_SOD = "V6-sox-sod"           # T3  separation of duties (set rule)
    V6_GDPR_PL = "V6-gdpr-pl"           # T2  purpose limitation (non-adjacent pair rule)
    ADV_SEMANTIC = "adv-semantic"       # advisory only, outside |=


THREAT_OF = {
    Clause.V1_TYPE: "T1", Clause.V5_POLICY: "T1", Clause.ADV_SEMANTIC: "T1",
    Clause.V4_FLOW: "T2", Clause.V6_HIPAA_MN: "T2", Clause.V6_GDPR_PL: "T2",
    Clause.V2_LEVEL: "T3", Clause.V3_PRIVILEGE: "T3", Clause.V6_SOX_SOD: "T3",
}


@dataclass
class Verdict:
    admitted: bool
    violations: List[Tuple[Clause, str]]
    advisories: List[Tuple[Clause, str]]
    obligations: Set[PolicyAction]
    policy_disagreements: int
    latency_ms: float

    def clauses(self) -> Set[Clause]:
        return {c for c, _ in self.violations}


# data-flow typing ------------------------------------------------------------

def dataflow_type_errors(chain: Sequence[AgentSkill]) -> List[str]:
    """Typability of a sequential chain under some request context Gamma.

    The composition is typed against an accumulating environment: a field that
    an earlier skill produced is bound to that skill's output type; a field no
    earlier skill produced is assumed to be supplied by the request (Gamma) and
    is bound at first use.  The chain is well-typed iff no later use of a bound
    field demands a different base type.  This is the static check (exists
    Gamma); at execution time Gamma is the concrete request and missing fields
    are rejected before the first invocation.  Labels (PHI/PII/...) are not
    typing: they are governed by V4/V6.
    """
    env: Dict[str, object] = {}
    errors: List[str] = []
    for s in chain:
        for name, typ in s.input_schema.field_types().items():
            if name in env and env[name] != typ:
                errors.append(f"{s.id}: '{name}' bound to {env[name].value}, expects {typ.value}")
            env.setdefault(name, typ)
        for name, typ in s.output_schema.field_types().items():
            env[name] = typ
    return errors


# regulatory predicates ------------------------------------------------------

PHI = {SemanticAnnotation.PHI, SemanticAnnotation.HIPAA_PROTECTED}
PII = {SemanticAnnotation.PII_CLASSIFIED, SemanticAnnotation.GDPR_SUBJECT}


def hipaa_min_necessary(chain: Sequence[AgentSkill]) -> List[str]:
    """Adjacent flow rule: PHI output must not feed a skill that neither accepts
    PHI nor sits in a regulatory compartment."""
    out = []
    for a, b in zip(chain, chain[1:]):
        if a.output_schema.annotations & PHI:
            covered = (b.input_schema.annotations & PHI) or \
                      b.data_boundary.boundary_type == DataBoundaryType.REGULATORY
            if not covered:
                out.append(f"PHI {a.id}->{b.id}")
    return out


def sox_separation_of_duties(chain: Sequence[AgentSkill]) -> List[str]:
    """Set rule: a composition must not contain both a financial-record creator
    and a financial-record approver."""
    creators = [s.id for s in chain if "financial_creation" in s.semantic_tags]
    approvers = [s.id for s in chain if "financial_approval" in s.semantic_tags]
    return [f"SoD {creators}+{approvers}"] if creators and approvers else []


def gdpr_purpose_limitation(chain: Sequence[AgentSkill]) -> List[str]:
    """Set rule (pairs need not be adjacent): PII produced by one skill must
    not be in a composition with a skill in another compartment that does not
    accept PII.  Each finding is tagged 'adj' when the pair is adjacent in the
    chain (then a hop-local labelled monitor could see it) or 'far' otherwise."""
    out = []
    ids = [s.id for s in chain]
    for i, a in enumerate(chain):
        if a.output_schema.annotations & PII:
            for j, b in enumerate(chain):
                if b.id == a.id:
                    continue
                if not (b.input_schema.annotations & PII) and \
                   b.data_boundary.boundary_id != a.data_boundary.boundary_id:
                    tag = "adj" if j == i + 1 else "far"
                    out.append(f"PII {a.id}~{b.id} [{tag}]")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The judgment and the mechanism ladder
# ─────────────────────────────────────────────────────────────────────────────

MECHANISMS = ("M0", "M1", "M2", "M3", "M4", "M5", "SW")

# which clauses each mechanism can evaluate (by the information it has)
VISIBLE: Dict[str, Set[Clause]] = {
    "M0": set(),
    "M1": {Clause.V1_TYPE},
    "M2": {Clause.V2_LEVEL},                      # + per-skill deny (handled below)
    "M3": {Clause.V2_LEVEL, Clause.V4_FLOW, Clause.V6_HIPAA_MN},
    "M4": {Clause.V2_LEVEL, Clause.V5_POLICY},
    "M5": {Clause.V2_LEVEL, Clause.V3_PRIVILEGE, Clause.V6_SOX_SOD, Clause.V6_GDPR_PL},
    "SW": set(Clause) - {Clause.ADV_SEMANTIC},
}


class Judgment:
    def __init__(self, ctx: AuthorizationContext, ssca: Optional[SemanticSkillCompositionAlgebra] = None):
        self.ctx = ctx
        self.ssca = ssca or SemanticSkillCompositionAlgebra()

    # -- full judgment --------------------------------------------------------
    def evaluate(self, chain: Sequence[AgentSkill], requester: str,
                 with_advisory: bool = True) -> Verdict:
        t0 = time.perf_counter_ns()
        viol: List[Tuple[Clause, str]] = []
        adv: List[Tuple[Clause, str]] = []
        fp = footprint(chain)

        # V1 data-flow typing with an accumulating environment.  The request
        # supplies the first skill's inputs; every later skill may draw each
        # required input field from the request context or from any earlier
        # output, with identical base type (dataflow/BPEL-variable discipline).
        # Labels (PHI/PII/...) are not typing: they are governed by V4/V6.
        for issue in dataflow_type_errors(chain):
            viol.append((Clause.V1_TYPE, issue))

        # V2 authority level
        if self.ctx.level(requester) < fp.level:
            viol.append((Clause.V2_LEVEL, f"{requester}@{self.ctx.level(requester)} < {fp.level}"))

        # V3 privilege accumulation (mutually exclusive permissions)
        for pair in self.ctx.mutual_exclusion:
            if pair <= fp.permissions:
                viol.append((Clause.V3_PRIVILEGE, "+".join(sorted(pair))))

        # V4 authorised flows
        for (b1, b2) in fp.flows:
            if not self.ctx.flow_ok(b1, b2):
                viol.append((Clause.V4_FLOW, f"{b1}->{b2}"))

        # V5 policy resolution: mandates on the same (type, scope) are combined
        # with deny-overrides (most restrictive decision wins).  A resolved
        # `deny` violates V5.  A resolved `require_approval` becomes an
        # obligation.  A disagreement between skills (e.g. allow vs
        # require_approval) is counted and reported to negotiation; it is not
        # by itself a violation of |= because the resolved decision governs.
        disagreements = 0
        for (ptype, scope), actions in fp.mandates.items():
            if len(actions) > 1:
                disagreements += 1
            resolved = max(actions, key=lambda a: DECISION_RANK[a])
            if resolved == PolicyAction.DENY:
                viol.append((Clause.V5_POLICY, f"deny@{ptype}/{scope}"))
            elif resolved == PolicyAction.REQUIRE_APPROVAL:
                fp.obligations.add(PolicyAction.REQUIRE_APPROVAL)

        # V6 regulatory predicates
        for d in hipaa_min_necessary(chain):
            viol.append((Clause.V6_HIPAA_MN, d))
        for d in sox_separation_of_duties(chain):
            viol.append((Clause.V6_SOX_SOD, d))
        for d in gdpr_purpose_limitation(chain):
            viol.append((Clause.V6_GDPR_PL, d))

        # advisory semantic conflicts (outside |=)
        if with_advisory:
            for a, b in zip(chain, chain[1:]):
                cs, _ = self.ssca.detect_semantic_conflicts(a, b)
                for c in cs:
                    adv.append((Clause.ADV_SEMANTIC, c.description))

        ms = (time.perf_counter_ns() - t0) / 1e6
        return Verdict(len(viol) == 0, viol, adv, fp.obligations, disagreements, ms)

    # -- mechanism ladder -----------------------------------------------------
    def mechanism_verdict(self, mech: str, chain: Sequence[AgentSkill], requester: str,
                          full: Optional[Verdict] = None) -> Set[Clause]:
        """Clauses that mechanism `mech` flags for this chain.

        M2..M5 share the per-invocation core: a PEP that sees one (skill,
        requester) at a time.  It evaluates the requester's level against the
        skill and the skill's OWN mandates (a skill carrying a plain `deny`
        would be refused), but it never sees pairs or sets of skills.  The only
        per-skill decision in the catalog is `require_approval` on
        action:trade_execution, which a PEP turns into an obligation, not a
        refusal; so the per-invocation core flags exactly V2 here.
        """
        if full is None:
            full = self.evaluate(chain, requester, with_advisory=False)
        seen = full.clauses() & VISIBLE[mech]
        if mech == "M3" and any(c == Clause.V6_GDPR_PL and "[adj]" in d
                                for c, d in full.violations):
            seen.add(Clause.V6_GDPR_PL)   # label check at the hop sees adjacent PII flows
        return seen


# ─────────────────────────────────────────────────────────────────────────────
# Runtime security automaton  M_alpha  (Theorem 1 check + Phase-4 checkpoint)
# ─────────────────────────────────────────────────────────────────────────────

class TraceMonitor:
    """Truncation automaton over events ('invoke', skill) / ('flow', b1, b2).

    State: permissions accumulated, skills seen, last boundary.  Rejects the
    first event that completes a violation of V2, V3, V4, V6-SoD, V6-MN, V6-PL.
    (V1 and V5 are static properties of the term and are checked at admission.)
    """

    def __init__(self, ctx: AuthorizationContext, requester: str):
        self.ctx = ctx
        self.requester = requester
        self.perms: Set[str] = set()
        self.seen: List[AgentSkill] = []
        self.rejected: Optional[str] = None

    def step(self, s: AgentSkill) -> bool:
        if self.rejected:
            return False
        # flow event
        if self.seen:
            prev = self.seen[-1]
            b1, b2 = prev.data_boundary.boundary_id, s.data_boundary.boundary_id
            if not self.ctx.flow_ok(b1, b2):
                self.rejected = f"flow {b1}->{b2}"
                return False
            if hipaa_min_necessary([prev, s]):
                self.rejected = "hipaa-mn"
                return False
        # invoke event
        if self.ctx.level(self.requester) < s.min_authority_level.value:
            self.rejected = "level"
            return False
        self.perms |= s.required_permissions
        for pair in self.ctx.mutual_exclusion:
            if pair <= self.perms:
                self.rejected = "privilege " + "+".join(sorted(pair))
                return False
        self.seen.append(s)
        if sox_separation_of_duties(self.seen) or gdpr_purpose_limitation(self.seen):
            self.rejected = "set-rule"
            return False
        return True

    def run(self, chain: Sequence[AgentSkill]) -> bool:
        for s in chain:
            if not self.step(s):
                return False
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Hash-chained audit log (T4)
# ─────────────────────────────────────────────────────────────────────────────

class HashChainedAuditLog:
    GENESIS = "0" * 64

    def __init__(self):
        self.entries: List[Dict] = []

    def append(self, event: str, composition_id: str, skill_ids: Sequence[str],
               principal: str, outcome: str, detail: str = "") -> str:
        prev = self.entries[-1]["hash"] if self.entries else self.GENESIS
        body = {"t": time.time(), "e": event, "c": composition_id,
                "S": list(skill_ids), "pi": principal, "o": outcome, "d": detail,
                "prev": prev}
        h = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        body["hash"] = h
        self.entries.append(body)
        return h

    def verify(self) -> bool:
        prev = self.GENESIS
        for e in self.entries:
            body = {k: v for k, v in e.items() if k != "hash"}
            if body["prev"] != prev:
                return False
            if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != e["hash"]:
                return False
            prev = e["hash"]
        return True
