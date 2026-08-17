"""Mutation spec for tools/audit/persona_audit.py.

The classifier's whole job is to refuse to call a persona operational when it
cannot execute. Every mutation here makes it say yes when the answer is no, which
is the only direction that matters: a false `routed-dead` costs a look, a false
`operational` is a router pointing at nothing and reporting coverage.
"""

TARGET = "tools/audit/persona_audit.py"
ARGV = ["selftest"]

MUTATIONS = [
    (
        "repo presence counts as live",
        "A persona whose skills exist in the repo but load nowhere reads as "
        "operational. This is the exact defect the tool was written for: the "
        "registry was authored against the payload and the runtime reads the "
        "live tree, which is why 7 personas were dead and nothing said so.",
        "        live_ok = [s for s in skills if (live / s).is_dir()]",
        "        live_ok = [s for s in skills if any((t / s).is_dir() for t in trees)]",
    ),
    (
        "every persona can write",
        "A persona owning to-prd or property-test-gen with no Edit or Write tool "
        "reads as operational, gets routed, gets spawned, and fails at the last "
        "step with the work already done.",
        "        can_write = tools is None or bool(set(tools) & WRITE_TOOLS)",
        "        can_write = True",
    ),
    (
        "no skill is a producer",
        "write-blocked can never be reached, so the tool reports zero of a defect "
        "it is the only thing measuring.",
        "        blocked = sorted(set(skills) & PRODUCERS) if not can_write else []",
        "        blocked = []",
    ),
    (
        "absent registry paths are never reported",
        "The registry keeps telling personas to use a corpus that is not on the "
        "machine, and the audit stops noticing.",
        "        if not p.exists():\n            gaps.append(m.group(1))",
        "        if p.exists():\n            gaps.append(m.group(1))",
    ),
    (
        "unresolved skills vanish",
        "A route to a skill that exists in no tree at all reads clean, which is "
        "how azure-cert-coach stayed in the registry pointing at nothing.",
        '"unresolved": sorted(set(skills) - set(resolves)),',
        '"unresolved": [],',
    ),
]
