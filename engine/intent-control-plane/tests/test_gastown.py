"""Tests for the Gastown persona-spec compiler (registry -> spawnable agent specs)."""
from __future__ import annotations

from intent_control_plane.gastown import (
    DEPTH_RUBRIC,
    find_persona,
    parse_registry,
    persona_spec,
)

_REGISTRY = """
## Persona Owners

### Mayor Opus

Role: lead orchestrator, routing, fanout, synthesis, escalation.

Owned skills:
- `agent-team`
- `brainstorming`
- `dispatch`

### Engineering Firm

Role: coding, TDD, simplification, local implementation quality.

Owned skills:
- `tdd`
- `code-simplifier`

### Role Only

Role: has a role but no owned-skills section, so it is not a spawnable persona.

## Best-Practices Corpus

### Not A Persona

Some other heading with no Role line.
"""


def test_parse_registry_extracts_personas_with_role_and_skills():
    personas = parse_registry(_REGISTRY)
    names = [p["name"] for p in personas]
    assert names == ["Mayor Opus", "Engineering Firm"]  # "Not A Persona" skipped (no Role:)
    mayor = personas[0]
    assert mayor["role"].startswith("lead orchestrator")
    assert mayor["skills"] == ["agent-team", "brainstorming", "dispatch"]


def test_find_persona_is_case_insensitive():
    personas = parse_registry(_REGISTRY)
    assert find_persona(personas, "engineering firm")["name"] == "Engineering Firm"
    assert find_persona(personas, "nobody") is None


def test_persona_spec_bakes_charter_skills_and_depth_rubric():
    personas = parse_registry(_REGISTRY)
    spec = persona_spec(personas[1])  # Engineering Firm
    assert spec["name"] == "Engineering Firm"
    assert spec["allowed_skills"] == ["tdd", "code-simplifier"]
    assert "Engineering Firm" in spec["system_prompt"]
    assert "tdd" in spec["system_prompt"]
    assert DEPTH_RUBRIC in spec["system_prompt"]
    # the domain depth essence (from ~/docs) is inserted, not just the generic rubric
    assert spec["depth_principles"]
    prompt = spec["system_prompt"].lower()
    assert "boundary contract" in prompt
    assert "no mocks" in prompt


def test_persona_spec_inserts_domain_depth_and_falls_back_for_unknown():
    ui = persona_spec({"name": "Product Studio", "role": "UI/UX craft", "skills": ["ui-ux-pro-max"]})
    prompt = ui["system_prompt"].lower()
    assert "shadcn" in prompt and "oklch" in prompt and "screenshot" in prompt  # Widgora depth
    # a persona with no curated principles still gets the generic rubric, empty principles
    unknown = persona_spec({"name": "Nobody Persona", "role": "x", "skills": ["y"]})
    assert unknown["depth_principles"] == []
    assert DEPTH_RUBRIC in unknown["system_prompt"]  # depth gate is baked into every spawn
