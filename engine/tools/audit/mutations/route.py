"""Mutations for tools/intent/route.py.

This file is the first thing in the estate that will run on EVERY prompt and change what
the model sees. `capture_turn.py` also runs on every prompt and changes nothing, because
it never writes to stdout; that is the difference, and it is the reason this one needs an
oracle that the other never did.

WHAT A REGRESSION COSTS HERE, which is not what it costs in a batch tool.

A collector that breaks reports nothing and somebody notices a quiet feed. A
UserPromptSubmit hook that breaks corrupts the input to every turn, including the turn
where somebody would have noticed. So the mutations below are weighted toward the two
failure modes that are invisible from inside a session:

  SILENT WRONGNESS. Routing that is unstable, or that names a persona nobody owns, is
  worse than routing that says nothing. The model is told this is a keyword match and to
  ignore it when wrong, but an unstable answer to the same prompt cannot be ignored
  consistently, and a persona that does not exist cannot be spawned at all.

  NOISE. A router that fires on everything is one the reader learns to skip, which is the
  exact death the agent feed measured on issue 38 in nineteen hours: 12 posts, 146 lines,
  0 reactions. `render_context` returning "" on no match is therefore load-bearing rather
  than a nicety, and it is mutated as such.

The registry parser is mutated separately from the routing, because they fail
differently. A broken parser produces skills with no owner, so the context names no
persona and the hook silently degrades to a skill list, which still looks like it is
working.
"""

TARGET = "engine/tools/intent/route.py"
ARGV = ["--selftest"]

MUTATIONS = [
    # ---- the two invisible failure modes ----
    ("the router fires on every prompt, matched or not",
     "noise. A router that always speaks is one the reader learns to skip, and it would "
     "be injected into every turn forever. Issue 38 measured what that costs: 12 posts "
     "and 146 item lines in nineteen hours with zero engagement",
     '    if not decision["matched"]:\n        return ""',
     '    if False:\n        return ""'),

    ("routing becomes order-dependent instead of weight-ordered",
     "a prompt hitting three QA Lab skills and one Release Bureau skill would name "
     "whichever regex sits earlier in the table. The primary persona is the one line of "
     "the injected context a model is most likely to act on, and picking it by table "
     "position is picking it arbitrarily",
     "    personas = sorted(tally, key=lambda p: (-tally[p], list(tally).index(p)))",
     "    personas = list(tally)"),

    # ---- the registry, which is the only source of persona names ----
    ("the registry parser stops reading heading sections",
     "every skill loses its owner, so the context degrades to a bare skill list while "
     "still rendering and still looking like it works. The hook would run on every turn, "
     "name no persona, and never move the 0-of-19 spawn count it exists to move",
     '        if line.startswith("### "):',
     '        if False:'),

    ("the parser attributes a skill to the LAST persona instead of the first",
     "setdefault is what makes ownership single, which the registry states as a rule: "
     "'Every skill has exactly one owning company persona.' Overwriting means a skill "
     "listed under two personas silently belongs to whichever appears later in the file, "
     "so editing an unrelated section changes routing",
     "                owner.setdefault(skill, persona)",
     "                owner[skill] = persona"),

    ("an empty registry invents ownership",
     "a missing or unreadable registry must produce no personas, not a default one. "
     "Naming a persona that no file owns sends a delegation to a subagent_type that does "
     "not exist, and the Agent tool's failure there is not something a hook can catch",
     "    owner: dict[str, str] = {}",
     '    owner: dict[str, str] = {"review": "Review Board"}'),

    # ---- the hook edge, where a failure breaks a turn ----
    ("the hook stops failing open",
     "this runs before every prompt. A router that can raise is a router that can break "
     "a turn, and the turn it breaks is the one where somebody would have noticed. "
     "Failing open and silent is the entire safety property of a UserPromptSubmit hook",
     "    except Exception:  # noqa: BLE001\n        pass\n    return 0",
     "    except Exception:  # noqa: BLE001\n        raise\n    return 0"),

    ("the emitted payload stops naming the hook event",
     "the harness keys on hookSpecificOutput.hookEventName to decide what the output "
     "means. A payload without it is ignored, so the hook runs, logs, costs time on every "
     "turn, and injects nothing. That is the worst shape available: a live component with "
     "no observable effect, which is what capture_turn.py already is",
     '    return json.dumps({"hookSpecificOutput": {\n        "hookEventName": "UserPromptSubmit", "additionalContext": ctx}})',
     '    return json.dumps({"hookSpecificOutput": {"additionalContext": ctx}})'),

    # ---- the rendered context, which is the whole product ----
    ("the context stops naming the delegation mechanism",
     "naming a persona without naming subagent_type leaves the reader with a label and "
     "no verb. The measured problem is not that personas are unknown, it is that 0 of 19 "
     "have ever been spawned across 66 transcripts while every delegation went to "
     "general-purpose",
     '        lines.append(\n            "If you delegate, prefer the Agent tool with subagent_type matching that "',
     '        lines.append(\n            "If you delegate, do what seems best. "  # was: subagent_type '),

    ("the prompt text is written into the routing ledger",
     "state/routing.jsonl is committed to git. tickets.py stores a text_sha and never the "
     "prompt for exactly this reason: a prompt corpus in version control is a different "
     "consent question than a routing corpus, and it is not one a hook may answer on the "
     "operator's behalf",
     '        log(decision, len(prompt), str(payload.get("session_id", "")))',
     '        log(decision, prompt, str(payload.get("session_id", "")))'),

    ("the session is read from CLAUDE_SESSION_ID again",
     "that variable is not exported into hook env on this host: the first 54 rows this "
     "file wrote all carried an empty session. spawn_log.py joins a spawn to a routing "
     "decision on exactly this field, so a blank one silently degrades every join to "
     "`newest routing row of ANY session`. With two parallel sessions, which this "
     "operator runs daily, a spawn in one is then compared against a prompt from the "
     "other and `agreed` becomes noise wearing the shape of evidence",
     '                "session": session,',
     '                "session": os.environ.get("CLAUDE_SESSION_ID", ""),'),

    ("a run with no registry reports the full verdict",
     "the false-green shape, in the one file here that runs before EVERY prompt. On a "
     "host with no registry the check silently does not run, and printing `names a real "
     "owner` would claim a property that was never measured. collect.py and spawn_log.py "
     "both narrow their verdicts; this file did not until a review caught it",
     '    return ("VERDICT (narrowed): routing is deterministic and silent on no match. NO live "',
     '    return ("VERDICT: routing is deterministic, silent on no match, and names a real owner. "'),

]
