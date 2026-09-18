from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional
from app.taxonomy.enums import canonical_key

@dataclass(frozen=True)
class CellRule:
    safety_tier: int
    gate_profile: str
    operator_default: str
    allowed_outputs: str

# NOTE: full 20,736 rules are large; we seed the DB from your Cell20736.csv if present.
# This module provides a small in-memory fallback and canonical key generation.

FALLBACK_RULE = CellRule(
    safety_tier=0,
    gate_profile="011⇄01-1",
    operator_default="MIX",
    allowed_outputs="summaries, outlines, checklists"
)

def make_key(domain_id: int, phase_id: int, state_id: int, lens_id: int) -> str:
    return canonical_key(domain_id, phase_id, state_id, lens_id)
