"""Mutations for tools/audit/skills_sync.py.

skills_sync.py guards itself against running on a host where the comparison
would be meaningless: a ~/.claude that is just a directory (created by a
container or a CI runner) rather than a real Claude installation. The guard
keyed on settings.json was added on 2026-08-10 after a container run reported
DRIFT: 87 against nothing.

Case 15 of the selftest pins both directions: a directory without
settings.json is NOT a deployment, and the same directory IS one once the
file appears. The mutations below re-break the guard, the survey, and the
classification logic that decides what gets reported.
"""

TARGET = "tools/audit/skills_sync.py"
ARGV = ["selftest"]

MUTATIONS = [
    # ---- host-shape guard: is_deployed_home() ----------------------------
    ("is_deployed_home keys on the directory instead of settings.json",
     "the exact defect that was found on 2026-08-05 in pointers.py and shipped "
     "unfixed here until 2026-08-10: a runner creates ~/.claude as a directory, "
     "the guard passes, and the survey compares this repo against a tree that "
     "was never a deployment of it",
     'return os.path.isfile(live_settings())',
     'return os.path.isdir(os.path.dirname(live_settings()))'),

    ("is_deployed_home always says yes",
     "the guard becomes a no-op: every host is a deployment, so a container "
     "reports a confident drift number against a tree nobody deployed",
     'return os.path.isfile(live_settings())',
     'return True'),

    ("is_deployed_home always says no",
     "the guard never opens: even a real deployment is reported as unmeasurable, "
     "so the domain that once produced a number now always exits 2",
     'return os.path.isfile(live_settings())',
     'return False'),

    # ---- cmd_check: the guard being used ---------------------------------
    ("cmd_check drops its is_deployed_home guard",
     "the filter that kept the survey honest is gone; a container runs the full "
     "comparison against a foreign tree and reports whatever it finds",
     '    if not is_deployed_home():',
     '    if False:'),

    ("cmd_check inverts its is_deployed_home guard",
     "a real deployment is reported as unmeasurable and a container is compared; "
     "the wrong half of every host population runs the check",
     '    if not is_deployed_home():',
     '    if is_deployed_home():'),

    # ---- classification: pointer vs real ---------------------------------
    ("a one-line dead-path skill stops being classified as pointer",
     "a skill whose body is just a path to nowhere is counted as real content "
     "and deployed, spreading the rot instead of reporting it",
     "    if n <= POINTER_MAX_LINES:\n        return \"pointer\", n, dead",
     "    if False:\n        return \"pointer\", n, dead"),

    ("a thin skill with dead paths stops being classified as pointer",
     "a 20-line skill naming /home/shovalbe is treated as real instead of hollow, "
     "so the contamination is invisible to the sync report",
     '    if n < THIN_MAX_LINES and dead:\n        return "pointer", n, dead',
     '    if False:\n        return "pointer", n, dead'),

    # ---- survey: squatter detection --------------------------------------
    ("files-where-directories-belong stop being scanned",
     "the first version of this checker was blind to 33 squatting files; this "
     "mutation re-breaks it",
     '        for name in listfiles(base):',
     '        for name in []:'),

    # ---- survey: drift detection -----------------------------------------
    ("byte-different copies are reported as same instead of drift",
     "two copies with different content read as in sync, so the domain passes "
     "on a tree that has never been deployed",
     '            out["drift"].append((name, os.path.getsize(a), os.path.getsize(b)))',
     '            out["same"].append(name)'),

    ("byte-identical copies are reported as drift instead of same",
     "every synced pair shows up as needing attention, so the signal is drowned "
     "and the report cries wolf",
     '            out["same"].append(name)',
     '            out["drift"].append((name, os.path.getsize(a), os.path.getsize(b)))'),

    # ---- report: exit code -----------------------------------------------
    ("a clean state returns exit 1 instead of 0",
     "a perfectly synced tree fails the check, which is the noise defect: a gate "
     "that always fails is not read",
     '    return 1 if bad else 0',
     '    return 1'),

    ("a drifted state returns exit 0 instead of 1",
     "the check stops enforcing: every drift number is green",
     '    return 1 if bad else 0',
     '    return 0'),
]
