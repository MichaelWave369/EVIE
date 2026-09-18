from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ---- 12 Domains ----
DOMAINS: Dict[int, str] = {
    1: "Body",
    2: "Mind",
    3: "Emotion",
    4: "Behavior",
    5: "Social",
    6: "Environment",
    7: "Work",
    8: "Money",
    9: "Learning",
    10: "Health",
    11: "Meaning",
    12: "Meta",
}

# ---- 12 Phases ----
PHASES: Dict[int, str] = {
    1: "Input",
    2: "Detection",
    3: "Activation",
    4: "Amplification",
    5: "Stabilization",
    6: "Integration",
    7: "Translation",
    8: "Execution",
    9: "Feedback",
    10: "Review",
    11: "Boundary",
    12: "Archive",
}

# ---- 12 States ----
STATES: Dict[int, str] = {
    1: "Absent",
    2: "Latent",
    3: "Emerging",
    4: "Weak",
    5: "Partial",
    6: "Stable",
    7: "Strong",
    8: "Dominant",
    9: "Saturated",
    10: "Overload",
    11: "Collapse",
    12: "Reset",
}

@dataclass(frozen=True)
class Lens:
    id: int
    code: str
    name: str
    description: str
    safety_tier: int
    gate_profile: str
    operator_default: str
    allowed_outputs: str

# Lens table from your PivotSeed (LensCode uses Greek letters)
LENSES: Dict[int, Lens] = {
    1: Lens(1, "Φ", "Physical", "Measurable physical quantities and signals", 0, "011⇄01-1", "MIX", "metrics, measurements, charts"),
    2: Lens(2, "Β", "Biological", "Physiological and biological processes", 1, "011⇄01-1", "MIX", "physiology notes, symptom tags"),
    3: Lens(3, "Κ", "Cognitive", "Thought, perception, and reasoning", 1, "011⇄01-1", "MIX", "cognitive labels, hypotheses (non-medical)"),
    4: Lens(4, "Ε", "Emotional", "Affective and feeling-based states", 1, "011⇄01-1", "MIX", "affect labels, regulation cues"),
    5: Lens(5, "Η", "Behavioral", "Actions, habits, and responses", 1, "011⇄01-1", "MIX", "habits, actions, training prompts"),
    6: Lens(6, "Σ", "Social", "Relationships and interpersonal dynamics", 1, "011⇄01-1", "MIX", "roles, boundaries, conversation cues"),
    7: Lens(7, "Ι", "Informational", "Documents, knowledge, and signals", 0, "011⇄01-1", "MIX", "summaries, outlines, tables"),
    8: Lens(8, "Ω", "Systemic", "Systems, structure, and process", 0, "011⇄01-1", "MIX", "workflows, specs, checklists"),
    9: Lens(9, "Δ", "Boundary", "Constraints, consent, and gates", 0, "011⇄01-1", "MIX", "policies, permissions, audit"),
    10: Lens(10, "Λ", "Narrative", "Story, identity, and meaning-making", 0, "011⇄01-1", "MIX", "scripts, story beats, messaging"),
    11: Lens(11, "Ψ", "Signal-Coherence", "Coherence / stability / telemetry framing", 0, "011⇄01-1", "MIX", "metrics + interpretations"),
    12: Lens(12, "⧂", "Meta-Design", "Design patterns, templates, meta-structure", 0, "011⇄01-1", "MIX", "blueprints, templates, kits"),
}

def canonical_key(domain_id: int, phase_id: int, state_id: int, lens_id: int) -> str:
    code = LENSES[lens_id].code if lens_id in LENSES else str(lens_id)
    return f"D{domain_id}-P{phase_id}-S{state_id}-{code}"

# Fibonacci cadence helper
FIB_DAYS: List[int] = [1, 2, 3, 5, 8, 13]
