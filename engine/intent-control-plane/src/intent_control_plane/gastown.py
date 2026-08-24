"""Gastown personas as real spawnable agent-specs (the foundation for a Claude-Agent-SDK layer).

Today the router only NAMES personas (a routing label). This module turns the
gastown-company-registry into agent SPECS: for each persona, a system-prompt charter plus its
owned skills, shaped for ClaudeAgentOptions(system_prompt=..., allowed_tools/skills=...). The
actual live spawn (ClaudeSDKClient) is a separate slice that needs the claude-agent-sdk
dependency; this pure layer is stdlib-only and unit-tested.

The depth rubric is baked into every persona's system prompt so a spawned agent is driven to
iterate to craft, not stop at first pass (the depth-gap this system exists to close).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

REGISTRY = Path.home() / ".claude" / "rules" / "gastown-company-registry.md"

DEPTH_RUBRIC = (
    "Do not stop at first pass. Iterate until a senior in this role would ship it: self-critique "
    "against craft (depth, edge cases, polish, hierarchy), not just correctness. For UI, require a "
    "visual-review pass (screenshot diff) before returning. Name what you would improve, then "
    "improve it. A green gate is table stakes, not done."
)

# Per-persona depth essence, distilled from Shoval's ~/docs + ~/.claude/rules (the "extra hard-work
# steps a human expert does" for that domain). Inserted into each contract so depth is enforceable,
# not a wish. Personas without an entry get only the generic DEPTH_RUBRIC.
DEPTH_PRINCIPLES: dict[str, list[str]] = {
    "Engineering Firm": [
        "TDD vertical slices: RED before GREEN per behavior, never all-tests-then-all-code.",
        "No mocks for business logic, services, DB, or filesystem; use recorded fixtures or real components.",
        "Boundary contracts: typed DTOs both ways, no raw passthrough, validate upstream and fail closed "
        "(502 on bad upstream JSON), extract the client, typed errors, test valid/invalid-upstream/"
        "missing-config/missing-resource/timeout.",
        "Ponytail before commit: delete or reuse before adding; no monofiles, duplicate builders, or "
        "speculative scaffolds.",
        "Never claim done without a real command plus pasted output (pass/fail).",
    ],
    "Product Studio": [
        "Go through the shared shadcn/ui component shell; never hand-roll a per-widget <style> island "
        "(that is the diagnosed generic-AI cause).",
        "Use only the OKLCH design tokens, never raw hex; never pure-black background or glassmorphism on "
        "primary data.",
        "KPI numbers at 3 significant figures plus unit, tabular-nums; typographic hierarchy by weight, one "
        "font family.",
        "Every animation gated on prefers-reduced-motion and signalling a state change; no decorative, "
        "bouncy, or looping motion.",
        "WCAG AA and never colour-alone (pair with icon/text); any visual change needs a golden-master "
        "screenshot diff.",
    ],
    "QA Lab": [
        "Testing pyramid: unit + property (hypothesis invariants) + integration + regression; no mocks.",
        "Property tests at every data boundary and protocol contract; mutation target over 80%.",
        "Every production bug gets a permanent regression test; report findings non-binary (severity + "
        "confidence).",
    ],
    "Review Board": [
        "Ponytail: delete or reuse before adding; hunt dead code, overengineering, and duplicate builders.",
        "Find the missing verification and the reflection gaps; a green gate is table stakes, not done.",
    ],
    "Architecture Office": [
        "The PRD/spec is the control plane: reconcile it before planning; a new plan is only a PRD delta.",
        "One ADR per costly-to-reverse decision (Context/Decision/Consequences); docs-control-plane taxonomy.",
    ],
    "Evidence Clerk": [
        "Decision-grade: ground every claim in a source, command, or artifact; never present an unverified "
        "fact as settled.",
        "No fake completion: command + real output + pass/fail is the only evidence.",
    ],
    "Release Bureau": [
        "Production means merged-to-deploy-branch + deployed + live-smoked (fresh refs, generate-then-"
        "observe), not built-locally.",
        "Never push corporate repos or create Azure resources without explicit per-action OK.",
    ],
    "Security and Compliance Office": [
        "Mask PII at the model boundary by reversible tokenization; never raw PII into any LLM or MCP payload.",
        "Never read, echo, or commit secrets, tokens, or keys.",
    ],
}


def parse_registry(text: str) -> list[dict[str, Any]]:
    """Parse the registry markdown into persona records: {name, role, skills}.

    A persona is a `### <Name>` block that carries a `Role:` line and an `Owned skills:` bullet
    list. Blocks without both are skipped (headings that are not personas).
    """
    personas: list[dict[str, Any]] = []
    for block in re.split(r"^### ", text, flags=re.M)[1:]:
        lines = block.splitlines()
        name = lines[0].strip()
        role = ""
        skills: list[str] = []
        in_skills = False
        for raw in lines[1:]:
            line = raw.strip()
            low = line.lower()
            if low.startswith("role:"):
                role = line[5:].strip()
            elif low.startswith("owned skills:"):
                in_skills = True
            elif in_skills and line.startswith("- "):
                skill = line[2:].strip().strip("`")
                if skill:  # skip empty bullets ("- ") so they do not count as a skill
                    skills.append(skill)
            elif in_skills and line and not line.startswith("-"):
                in_skills = False
        # A persona needs a Role and at least one owned skill; a Role-only heading or an empty
        # Owned-skills section is not a spawnable persona (Codex review: no empty-skill agents).
        if name and role and skills:
            personas.append({"name": name, "role": role, "skills": skills})
    return personas


def find_persona(personas: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    """Case-insensitive persona lookup by name."""
    target = name.strip().lower()
    for persona in personas:
        if persona["name"].lower() == target:
            return persona
    return None


def persona_spec(persona: dict[str, Any]) -> dict[str, Any]:
    """A ClaudeAgentOptions-shaped spec for spawning this persona via the Claude Agent SDK.

    system_prompt = the persona's charter (role + owned skills + the depth rubric);
    allowed_skills = its owned skills (the SDK's allowed_tools/skills allowlist).
    """
    name = persona["name"]
    role = persona["role"]
    skills = persona.get("skills", [])
    principles = DEPTH_PRINCIPLES.get(name, [])
    parts = [
        f"You are the {name} in the Gastown virtual company. Your role: {role} "
        f"You own these skills: {', '.join(skills) if skills else 'none'}."
    ]
    if principles:
        parts.append(
            "Your domain depth standards (from Shoval's ~/docs; a senior in this role holds every one):"
        )
        parts.extend(f"- {p}" for p in principles)
    parts.append(DEPTH_RUBRIC)
    return {
        "name": name,
        "system_prompt": "\n".join(parts),
        "allowed_skills": skills,
        "depth_principles": principles,
    }
