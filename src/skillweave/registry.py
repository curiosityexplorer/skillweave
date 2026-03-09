"""
Enterprise Skill Registry (ESR) — Section VIII of the paper.

Implements:
  - Skill Catalog with semantic search (VIII.A)
  - Provenance Tracker
  - Version Manager with composition compatibility
  - Access Controller aligned with OPH
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .models import (
    AgentSkill, AuthorityLevel, OrganizationalPrincipal, SkillVersion,
)


class SkillLifecycleState:
    DRAFT = "draft"
    PUBLISHED = "published"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

    VALID_TRANSITIONS = {
        DRAFT: {PUBLISHED},
        PUBLISHED: {ACTIVE, ARCHIVED},
        ACTIVE: {DEPRECATED},
        DEPRECATED: {ARCHIVED},
        ARCHIVED: set(),
    }


@dataclass
class SkillRegistryEntry:
    """A registered skill with provenance and lifecycle metadata."""
    skill: AgentSkill
    state: str = SkillLifecycleState.ACTIVE
    author_principal_id: str = ""
    organization_unit: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    test_results: Dict[str, Any] = field(default_factory=dict)
    deployment_count: int = 0
    composition_count: int = 0
    dependent_compositions: List[str] = field(default_factory=list)


class EnterpriseSkillRegistry:
    """
    Governed registry for organizational skill assets.
    Provides catalog, provenance, versioning, and access control.
    """

    def __init__(self):
        self.entries: Dict[str, SkillRegistryEntry] = {}
        self.access_log: List[Dict[str, Any]] = []

    def register_skill(
        self, skill: AgentSkill, author_principal_id: str, org_unit: str = ""
    ) -> SkillRegistryEntry:
        """Register a new skill in the catalog."""
        entry = SkillRegistryEntry(
            skill=skill,
            state=SkillLifecycleState.ACTIVE,
            author_principal_id=author_principal_id,
            organization_unit=org_unit,
            created_at=time.time(),
            updated_at=time.time(),
        )
        self.entries[skill.id] = entry
        return entry

    def get_skill(self, skill_id: str) -> Optional[AgentSkill]:
        entry = self.entries.get(skill_id)
        return entry.skill if entry else None

    def get_entry(self, skill_id: str) -> Optional[SkillRegistryEntry]:
        return self.entries.get(skill_id)

    def search_by_tags(self, tags: Set[str]) -> List[AgentSkill]:
        """Semantic search: find skills whose tags overlap with query."""
        results = []
        for entry in self.entries.values():
            if entry.state == SkillLifecycleState.ACTIVE:
                overlap = entry.skill.semantic_tags & tags
                if overlap:
                    results.append(entry.skill)
        return results

    def search_compatible(
        self, output_schema, max_results: int = 10
    ) -> List[AgentSkill]:
        """Find skills whose input schema is compatible with the given output."""
        results = []
        for entry in self.entries.values():
            if entry.state == SkillLifecycleState.ACTIVE:
                compatible, _ = output_schema.is_compatible_with(entry.skill.input_schema)
                if compatible:
                    results.append(entry.skill)
                    if len(results) >= max_results:
                        break
        return results

    def check_version_compatibility(
        self, skill_id_1: str, skill_id_2: str
    ) -> bool:
        """Check if two skills have compatible versions for composition."""
        e1 = self.entries.get(skill_id_1)
        e2 = self.entries.get(skill_id_2)
        if not e1 or not e2:
            return False
        return e1.skill.version.is_compatible_with(e2.skill.version)

    def record_composition(self, composition_id: str, skill_ids: List[str]):
        """Record a composition event for provenance tracking."""
        for sid in skill_ids:
            entry = self.entries.get(sid)
            if entry:
                entry.composition_count += 1
                entry.dependent_compositions.append(composition_id)

    @property
    def active_skill_count(self) -> int:
        return sum(1 for e in self.entries.values()
                   if e.state == SkillLifecycleState.ACTIVE)

    @property
    def total_skill_count(self) -> int:
        return len(self.entries)
