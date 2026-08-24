"""Mutations for tools/snapshot/snap.py.

This tool exists to replace a one-deep fixed-name backup, and it writes into a
git-tracked directory while reading a tree that holds credentials. Both of those
make its checks worth more than usual, and both make a decorative check worse than
usual: a snapshot that silently captures nothing still exits 0 and still looks like
an undo, and a secret filter that never fires looks exactly like one that has
nothing to find.

So the entries below break, one at a time: the collision loop whose absence WAS the
original defect, every deny rule, both directions of the secret filter, every
verify failure mode, every drift class, and each of restore's refusals.
"""

TARGET = "engine/tools/snapshot/snap.py"
ARGV = ["selftest"]

MUTATIONS = [
    # --- the defect this tool was written to replace --------------------------
    ("new_id stops avoiding a collision",
     "the original sync-live-settings defect: the second take overwrites the first",
     '    sid, n = base, 1\n    while (SNAPDIR / sid).exists():\n'
     '        n += 1\n        sid = "{}-{}".format(base, n)\n    return sid',
     '    return base'),

    ("a take overwrites an existing snapshot directory instead of refusing",
     "exist_ok=True turns a collision into silent data loss inside the snapshot",
     '    dest_root.mkdir(parents=True, exist_ok=False)',
     '    dest_root.mkdir(parents=True, exist_ok=True)'),

    # --- the deny rules, which stand between a credential and a git tree ------
    ("classify stops denying by filename",
     ".credentials.json and the setup token get copied into the repo",
     '    if parts[-1] in DENY_NAMES:\n        return "denied name: " + parts[-1]',
     ''),

    ("classify stops denying by directory name",
     "a backups/ or __pycache__/ nested in an allowlisted tree is swept in",
     '    hit = next((p for p in parts if p in DENY_PARTS), "")\n'
     '    if hit:\n        return "denied directory: " + hit',
     '    hit = ""'),

    ("classify stops denying by suffix",
     "the OAuth screenshot and every .jsonl transcript become capturable",
     '    suf = PurePosixPath(rel).suffix.lower()\n'
     '    if suf in DENY_SUFFIXES:\n        return "denied suffix: " + suf',
     ''),

    ("the include list stops being the default-deny boundary",
     "an unrecognised file is captured by default, which is the wrong default here",
     '    return "not on the include list"',
     '    return ""'),

    ("candidates stops offering top-level files to classify",
     "settings.json and CLAUDE.md, the whole point, are never captured",
     '        if child.is_file():\n            files.append((child.name, child))',
     '        if False:\n            pass'),

    # --- the secret filter, both directions ----------------------------------
    ("the secret scan always reports clean",
     "a key inside an allowlisted hook is copied into a git-tracked tree",
     '    for name, pat in SECRET_PATTERNS:\n        if re.search(pat, blob):\n'
     '            return "matched secret pattern " + name\n    return ""',
     '    return ""'),

    ("the secret scan flags every file",
     "nothing is ever captured and every restore is empty, silently",
     '        if re.search(pat, blob):',
     '        if True:'),

    ("a hash-only entry gets its content copied anyway",
     "the filter computes the right verdict and the writer ignores it",
     '        if e["captured"]:\n            dest = dest_root / rel',
     '        if True:\n            dest = dest_root / rel'),

    ("the hash-only reason carries the matched text instead of the pattern name",
     "the secret lands in a git-tracked manifest by way of its own warning",
     '    return "matched secret pattern " + name',
     '    return "matched secret pattern " + name + ": " + blob.decode(errors="replace")'),

    # --- verify: does the snapshot still match its own manifest ---------------
    ("verify stops rehashing captured files",
     "a corrupted or edited snapshot reports clean, so restore writes garbage",
     '            elif sha256_file(p) != e["sha256"]:',
     '            elif False:'),

    ("verify stops reporting a captured file that vanished",
     "a snapshot missing half its content passes, and restore quietly skips it",
     '            if not p.is_file():\n                bad.append("MISSING   " + e["path"])',
     '            if not p.is_file():\n                pass'),

    ("verify stops treating a leaked hash-only file as a problem",
     "content that was deliberately withheld can reappear with nothing noticing",
     '        elif p.exists():\n'
     '            bad.append("LEAKED    {} (hash-only entry has content in the snapshot)"\n'
     '                       .format(e["path"]))',
     '        elif False:\n            pass'),

    ("verify stops checking an entry against the current deny lists",
     "a snapshot taken under a looser policy keeps passing forever",
     '        why = classify(e["path"])\n'
     '        if why:\n'
     '            bad.append("NOWDENIED {} ({} under the current deny lists)"\n'
     '                       .format(e["path"], why))',
     ''),

    ("verify stops noticing snapshot content its manifest never mentions",
     "content nothing ever classified or hashed sits in the snapshot unremarked",
     '        if rel not in known:\n'
     '            bad.append("ORPHAN    {} (in the snapshot, absent from its manifest)"\n'
     '                       .format(rel))',
     ''),

    ("verify stops re-scanning captured bytes for secrets",
     "a take whose filter was wrong is never contradicted by a second opinion",
     '        reason = secret_reason(root / rel)\n'
     '        if reason:\n'
     '            bad.append("SECRET    {} ({})".format(rel, reason))',
     ''),

    ("verify always exits 0",
     "the table still prints the problems and every caller sees green",
     '    return 1 if bad else 0',
     '    return 0'),

    # --- drift detection, which is the half that works from a fresh clone -----
    ("compare_to_live stops comparing hashes",
     "an edited live file reads as unchanged, so drift is invisible",
     '        same = sha256_file(live) == e["sha256"]',
     '        same = True'),

    ("a live file that disappeared is counted as unchanged",
     "a deleted hook stops being drift, which is the deletion you most want to see",
     '        if not live.is_file():\n            out["gone"].append(rel)\n            continue',
     '        if not live.is_file():\n            out["unchanged"].append(rel)\n            continue'),

    ("compare_to_live stops noticing files that appeared after the snapshot",
     "a new hook added since the snapshot is invisible to diff and to restore",
     '    for rel, _abs in candidates()[0]:\n'
     '        if not classify(rel) and rel not in by_path:\n'
     '            out["added"].append(rel)',
     ''),

    ("a hash-only file that changed stops counting as drift",
     "the one reason to record a hash without the bytes is thrown away",
     '            out["hash_only" if same else "changed"].append(rel)',
     '            out["hash_only"].append(rel)'),

    ("diff stops honouring --fail-on-drift",
     "the flag a verifier would depend on is a no-op, so a claim on it cannot fail",
     '    if a.fail_on_drift and drift:\n        return 1',
     '    pass'),

    # --- restore: the three things it must refuse to do ----------------------
    ("a dry-run restore writes anyway",
     "the safe form of the destructive command stops being safe",
     '    if not a.apply:',
     '    if False:'),

    ("restore skips its own pre-restore snapshot",
     "restoring becomes the one action in this tool that cannot be undone",
     '    pre = do_take(label="pre-restore-" + a.id, quiet=True)\n'
     '    print("  took {} first, so this restore is itself revertable".format(pre))',
     '    pass'),

    ("restore tries to write hash-only entries it never captured",
     "the withheld-content bookkeeping is computed and then ignored",
     '    writes = [r for r in d["changed"] + d["gone"] if by_path[r].get("captured")]',
     '    writes = list(d["changed"]) + list(d["gone"])'),

    ("restore stops naming the files it left in place",
     "the operator is not told which live files the snapshot does not account for",
     '    for rel in d["added"]:\n'
     '        print("  LEFT      {}  (appeared after the snapshot; restore never "\n'
     '              "deletes)".format(rel))',
     '    pass'),

    ("restore exits 0 even when it could not restore everything",
     "a partial restore is indistinguishable from a complete one",
     '    return 1 if unrestorable else 0',
     '    return 0'),

    # --- the manifest is the git-tracked half, so its shape is a contract -----
    ("the manifest stops recording which directories were left unwalked",
     "coverage is overstated: a skipped tree looks like a tree with no files",
     '        "not_walked": not_walked,',
     '        "not_walked": [],'),

    ("the manifest schema version stops being written",
     "a later reader cannot tell which layout it is looking at",
     '        "schema": SCHEMA,',
     '        "schema": 0,'),
]
