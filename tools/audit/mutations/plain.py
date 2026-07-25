"""Mutation spec for dot-claude/skills/explain-simply/plain.py.

Why a style checker of all things needs one. A readability check is the easiest
kind of check to fake: it reads text, prints something reassuring, and exits 0
whether or not any rule inside it is reachable. A threshold set to 250 words, a
deny list nothing can match, a jargon table that went empty in a refactor -- each
looks exactly like a working check from the outside, and each would let this repo
keep claiming its writing is measured when nothing measures it.

So every guarantee plain.py makes gets broken here, one at a time, and its
selftest must go red. Two classes of mutation matter more than the rest:

  boundary flips (`>` to `>=`, `<=` to `<`) are the ones a human review misses.
  They keep every fixture passing except the one sitting exactly on the limit,
  which is why plain.py's selftest plants text at exactly 25 words, exactly a
  20-word average, exactly half active, and exactly five sentences.

  reachability kills (a regex that can no longer match, a table replaced by an
  empty one) are the failure this repo has actually shipped: a deny rule no
  candidate path could reach, and a checker that reported success having
  examined zero items. A rule that cannot fire and a rule with nothing to find
  print the same thing.
"""

TARGET = "dot-claude/skills/explain-simply/plain.py"
ARGV = ["selftest"]

MUTATIONS = [
    # --- sentence length -------------------------------------------------
    ("sentence_limit_raised",
     "the 25-word ceiling is set so high nothing can exceed it",
     "MAX_SENTENCE_WORDS = 25",
     "MAX_SENTENCE_WORDS = 250"),
    ("sentence_limit_off_by_one",
     "a sentence sitting exactly on the limit is reported as over it",
     "if n > MAX_SENTENCE_WORDS:",
     "if n >= MAX_SENTENCE_WORDS:"),

    # --- average sentence length -----------------------------------------
    ("avg_limit_raised",
     "the 20-word average ceiling can no longer be exceeded",
     "MAX_AVG_WORDS = 20",
     "MAX_AVG_WORDS = 200"),
    ("avg_limit_off_by_one",
     "an average sitting exactly on the limit is reported as over it",
     "if avg > MAX_AVG_WORDS:",
     "if avg >= MAX_AVG_WORDS:"),

    # --- active voice ratio ----------------------------------------------
    ("active_ratio_floor_removed",
     "the active-voice floor drops to zero, so no document can fail it",
     "MIN_ACTIVE_RATIO = 0.5",
     "MIN_ACTIVE_RATIO = 0.0"),
    ("active_ratio_boundary_relaxed",
     "exactly half active passes, though the rule needs MORE than half",
     "active_ratio <= MIN_ACTIVE_RATIO",
     "active_ratio < MIN_ACTIVE_RATIO"),

    # --- passive detection internals -------------------------------------
    ("passive_ed_branch_dead",
     "the -ed participle branch can never match, leaving only irregulars",
     'cand.endswith("ed") and len(cand) > 4',
     'cand.endswith("zz") and len(cand) > 4'),
    ("passive_bare_be_guard_inverted",
     "a modal-plus-been passive is skipped instead of caught",
     "toks[i - 1] not in PRE_BE",
     "toks[i - 1] in PRE_BE"),
    ("passive_false_friend_ignored",
     "an adjectival be-complement is reported as passive",
     "if cand in PARTICIPLE_FALSE_FRIENDS:\n                break",
     "if cand in PARTICIPLE_FALSE_FRIENDS:\n                pass"),

    # --- hidden verbs -----------------------------------------------------
    ("hidden_verb_ysis_suffix_dropped",
     "the source's own worked example, 'conduct an analysis of', stops matching",
     '"ysis", "yses")',
     '"ysisX", "yses")'),
    ("hidden_verb_length_gate_raised",
     "no nominalization is long enough to be seen",
     "if len(cand) > 6 and cand.endswith(NOMINAL_SUFFIXES):",
     "if len(cand) > 60 and cand.endswith(NOMINAL_SUFFIXES):"),
    ("hidden_verb_window_collapsed",
     "the look-ahead window is empty, so nothing follows a linking verb",
     "for j in range(i + 1, min(i + 4, len(toks))):",
     "for j in range(i + 1, min(i + 1, len(toks))):"),

    # --- acronyms ---------------------------------------------------------
    ("acronym_expansion_test_inverted",
     "an expanded acronym is reported and an unexplained one is not",
     "if not expanded:",
     "if expanded:"),
    ("acronym_wellknown_list_bypassed",
     "JSON and URL are reported as unexplained jargon",
     "if acr in WELL_KNOWN_ACRONYMS or acr in seen:",
     "if acr in seen:"),

    # --- jargon tables ----------------------------------------------------
    ("jargon_phrase_table_emptied",
     "the wordy-phrase table is unreachable while single words still fire",
     "for phrase, better in JARGON_PHRASES.items():",
     "for phrase, better in {}.items():"),
    ("jargon_word_table_emptied",
     "the single-word table is unreachable while phrases still fire",
     "for word, better in JARGON.items():",
     "for word, better in {}.items():"),

    # --- unbacked numbers (this repo's own rule) --------------------------
    ("number_shape_unmatchable",
     "no token can be recognised as a bare numeral at all",
     'if not re.fullmatch(r"\\d[\\d,]*(?:\\.\\d+)?%?", tok):',
     'if not re.fullmatch(r"\\d[\\d,]*(?:\\.\\d+)?%?X", tok):'),
    ("number_code_backing_ignored",
     "a numeral a command output already carries is still reported",
     'if digits in code or digits.replace(",", "") in code.replace(",", ""):',
     "if False:"),
    ("number_year_exemption_broken",
     "a plain year is reported as an unbacked number",
     'if re.fullmatch(r"(?:19|20)\\d\\d", digits):',
     'if re.fullmatch(r"(?:19|20)\\d\\d\\d", digits):'),

    # --- extraction: what gets measured at all ---------------------------
    ("fenced_code_left_in_prose",
     "a fenced block is measured as prose, corrupting every length number",
     'body = re.sub(r"```.*?```", eat, body, flags=re.S)',
     'body = re.sub(r"```zzz```", eat, body, flags=re.S)'),
    ("inline_code_left_in_prose",
     "inline code is measured as prose and stops backing any numeral",
     'body = re.sub(r"`[^`\\n]+`", eat, body)',
     'body = re.sub(r"zzz[^`\\n]+zzz", eat, body)'),
    ("headings_left_in_prose",
     "a heading merges into the paragraph below it",
     'if stripped.startswith("#"):',
     'if stripped.startswith("\\x01"):'),
    ("urls_left_in_prose",
     "a URL is counted as words and its digits as unbacked numbers",
     'body = re.sub(r"https?://\\S+", " ", body)',
     'body = re.sub(r"https?://\\S+ZZZ", " ", body)'),
    ("frontmatter_left_in_prose",
     "YAML metadata is measured as if it were writing",
     'end = body.find("\\n---", 4)',
     'end = body.find("\\nZZZ---", 4)'),
    ("list_item_text_destroyed",
     "stripping a bullet's marker throws the bullet's own text away",
     "kept.append(line[marker.end():])",
     'kept.append("")'),
    ("list_items_not_separated",
     "a run of bullets is measured as one long paragraph",
     'marker = re.match(r"^\\s*(?:[-*+]|\\d+\\.)\\s+", line)',
     'marker = re.match(r"^\\s*ZZZ\\s+", line)'),

    # --- the report contract ---------------------------------------------
    ("advisory_promoted_to_violation",
     "an over-reporting passive note alone turns a clean document red",
     'ADVISORY = {"passive_sentence"}',
     "ADVISORY = set()"),
    ("findings_keys_collapsed",
     "every check writes to one key, so any finding satisfies any assertion",
     "findings.setdefault(name, []).append(item)",
     'findings.setdefault("finding", []).append(item)'),
    ("exit_code_always_green",
     "findings are printed and the exit code stays 0",
     "return 1 if violations else 0",
     "return 0"),
    ("unreadable_path_reported_clean",
     "a file that cannot be read exits 0 instead of 2",
     "            return 2",
     "            return 0"),
]
