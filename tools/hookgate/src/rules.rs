// GENERATED from ~/.claude/hooks/safety_gate.py::RULES. Do not hand-edit.
//
// `pattern` is a byte-for-byte copy; inline flags (?i)/(?is) carry the Python flags.
//
// `literal_groups` is the PRESCAN, a conjunction of disjunctions: EVERY group must have at
// least one member present in the lowercased command before the pattern is worth compiling. Compiling all 17 patterns measured ~45 ms of the gate's ~49 ms
// on Linux, so skipping the ones that cannot match is where the remaining cost goes.
//
// Over-approximating a literal set is free (a wasted compile). UNDER-approximating silently
// skips a rule on a command it should block. regen_rules.py fuzzes every set before emitting
// this file and refuses to write if `pattern.search(s)` ever holds with no literal present.
//
// Regenerate with tools/hookgate/regen_rules.py after any change to safety_gate.py, then
// re-run tools/hookgate/diff_oracle.py, which is the only thing proving the engines agree.

pub struct Rule {
    pub pattern: &'static str,
    pub reason: &'static str,
    pub literal_groups: &'static [&'static [&'static str]],
}

pub const RULES: &[Rule] = &[
    Rule {
        pattern: r#"(?is)\brm\s+(?=[^\r\n]*(?:-[a-z]*r[a-z]*|--recursive))[^\r\n]*(?:\s+[\"']?(?:/|~(?:/|\s|[\"']?$)|\$HOME|[A-Za-z]:[\\/](?:\s|[\"']?$)|[A-Za-z]:[\\/]Users[\\/][^\\/\s\"']+(?:[\\/]?[\"']?(?:\s|$))|\.git(?:/|\s|[\"']?$)))"#,
        reason: r#"Recursive deletion of a broad, home, root, or Git target is blocked."#,
        literal_groups: &[&[r#"rm"#]],
    },
    Rule {
        pattern: r#"(?is)(?:^|[;&|]\s*)remove-item\b(?=[^\r\n]*-(?:recurse|r)\b)[^\r\n]*(?:[A-Za-z]:\\(?:\s|[\"']?$)|\\Users\\[^\\\s]+(?:\s|[\"']?$)|\$HOME|~(?:\\|\s|[\"']?$)|\.git)"#,
        reason: r#"Recursive PowerShell deletion of a broad, home, or Git target is blocked."#,
        literal_groups: &[&[r#"remove-item"#]],
    },
    Rule {
        pattern: r#"(?is)(?:^|[;&|]\s*)(?:cmd(?:\.exe)?\s+/[ck]\s+)?(?:rd|rmdir)\b(?=[^\r\n]*/s\b)[^\r\n]*(?:[A-Za-z]:[\\/](?:\s|[\"']?$)|[A-Za-z]:[\\/]Users[\\/][^\\/\s\"']+(?:[\\/]?[\"']?(?:\s|$))|%USERPROFILE%|\.git)"#,
        reason: r#"Recursive cmd deletion of a broad, home, or Git target is blocked."#,
        literal_groups: &[&[r#"rd"#, r#"rmdir"#], &[r#"/s"#]],
    },
    Rule {
        pattern: r#"(?i)\bgit\b[^\r\n;&|]{0,400}\breset\s+--hard\b"#,
        reason: r#"git reset --hard can discard work and is blocked."#,
        literal_groups: &[&[r#"git"#], &[r#"reset"#]],
    },
    Rule {
        pattern: r#"(?i)\bgit\b[^\r\n;&|]{0,400}\bclean\b[^\r\n;&|]*-[a-z]*f"#,
        reason: r#"Forced git clean can delete untracked work and is blocked."#,
        literal_groups: &[&[r#"git"#], &[r#"clean"#]],
    },
    Rule {
        pattern: r#"(?i)\bgit\b[^\r\n;&|]{0,400}\bbranch\b[^\r\n;&|]*(?:\s-D\b|--delete\b[^\r\n;&|]*--force\b|--force\b[^\r\n;&|]*--delete\b|\s-d\b[^\r\n;&|]*\s-f\b)"#,
        reason: r#"Forced branch deletion is blocked."#,
        literal_groups: &[&[r#"git"#], &[r#"branch"#]],
    },
    Rule {
        pattern: r#"(?i)\bgit\b[^\r\n;&|]{0,400}\bpush\b[^\r\n;&|]*(?:--force(?:-with-lease)?|-f)\b"#,
        reason: r#"Force-push is blocked."#,
        literal_groups: &[&[r#"git"#], &[r#"push"#]],
    },
    Rule {
        pattern: r#"(?i)\bgit\b[^\r\n;&|]{0,400}\bpush\b[^\r\n;&|]*(?:--delete\b|--mirror\b|--prune\b|(?:^|\s)[+:][^\s]+)"#,
        reason: r#"Remote ref deletion, mirror push, or forced refspec is blocked."#,
        literal_groups: &[&[r#"git"#], &[r#"push"#]],
    },
    Rule {
        pattern: r#"(?i)\bgit\b[^\r\n;&|]{0,400}\bcheckout\b[^\r\n;&|]{0,240}\s--\s+"#,
        reason: r#"git checkout -- can discard worktree changes and is blocked."#,
        literal_groups: &[&[r#"git"#], &[r#"checkout"#]],
    },
    Rule {
        pattern: r#"(?i)\bgit\b[^\r\n;&|]{0,400}\bcheckout\b(?:[^\r\n;&|]*(?:-f|--force)\b|[^\r\n;&|]*\s\.\s*$)"#,
        reason: r#"Forced checkout or checkout of the whole worktree can discard changes and is blocked."#,
        literal_groups: &[&[r#"git"#], &[r#"checkout"#]],
    },
    Rule {
        pattern: r#"(?i)\bgit\b[^\r\n;&|]{0,400}\bswitch\b[^\r\n;&|]*--discard-changes\b"#,
        reason: r#"git switch --discard-changes can discard worktree changes and is blocked."#,
        literal_groups: &[&[r#"git"#], &[r#"switch"#]],
    },
    Rule {
        pattern: r#"(?i)\bgit\b[^\r\n;&|]{0,400}\brestore\b[^\r\n;&|]*--worktree\b"#,
        reason: r#"git restore --worktree can discard worktree changes and is blocked."#,
        literal_groups: &[&[r#"git"#], &[r#"restore"#]],
    },
    Rule {
        pattern: r#"(?i)\bgit\b[^\r\n;&|]{0,400}\brestore\b(?![^\r\n;&|]*--staged\b)"#,
        reason: r#"git restore can discard worktree changes and is blocked unless it only unstages."#,
        literal_groups: &[&[r#"git"#], &[r#"restore"#]],
    },
    Rule {
        pattern: r#"(?i)(?:curl|wget|iwr|irm)\b[^\r\n|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh|pwsh|powershell|iex)\b"#,
        reason: r#"Piping a network response directly into a shell is blocked."#,
        literal_groups: &[&[r#"curl"#, r#"wget"#, r#"iwr"#, r#"irm"#]],
    },
    Rule {
        pattern: r#"(?is)\b(?:cat|type|get-content|gc|head|tail|sed|awk|base64|xxd|strings|less|more|certutil)\b[^\r\n]*(?:\.env(?:\.(?:local|production|staging|development|test|[^.\s\"']+\.local))?|\.ssh[\\/][^\\/\s\"']+|credentials?\.(?:json|ya?ml|ini|txt)|service[_-]?account[^\\/\s\"']*\.json|id_(?:rsa|ed25519)|[^\\/\s\"']+\.(?:pem|key))(?:[\"']?(?:\s|$)|[)\]}])"#,
        reason: r#"Printing a likely credential file into model-visible output is blocked."#,
        literal_groups: &[&[r#"cat"#, r#"type"#, r#"get-content"#, r#"gc"#, r#"head"#, r#"tail"#, r#"sed"#, r#"awk"#, r#"base64"#, r#"xxd"#, r#"strings"#, r#"less"#, r#"more"#, r#"certutil"#], &[r#".env"#, r#".ssh"#, r#"credential"#, r#"service"#, r#"id_rsa"#, r#"id_ed25519"#, r#".pem"#, r#".key"#]],
    },
    Rule {
        pattern: r#"(?is)\b(?:rg|grep|findstr|select-string|more)\b[^\r\n;&|]{0,500}(?:^|\s)[\"']?(?:\.env(?:\.(?:local|production|staging|development|test|[^.\s\"']+\.local))?|\.ssh[\\/][^\\/\s\"']+|credentials?\.(?:json|ya?ml|ini|txt)|service[_-]?account[^\\/\s\"']*\.json|id_(?:rsa|ed25519)|[^\\/\s\"']+\.(?:pem|key))[\"']?(?:\s|$)"#,
        reason: r#"A command that may print a credential file into model-visible output is blocked."#,
        literal_groups: &[&[r#"rg"#, r#"grep"#, r#"findstr"#, r#"select-string"#, r#"more"#], &[r#".env"#, r#".ssh"#, r#"credential"#, r#"service"#, r#"id_rsa"#, r#"id_ed25519"#, r#".pem"#, r#".key"#]],
    },
    Rule {
        pattern: r#"(?is)\b(?:python(?:3)?|py|powershell|pwsh|cmd|node|ruby|perl|php)\b[^\r\n;&|]{0,700}(?:\.env(?:\.(?:local|production|staging|development|test|[^.\s\"']+\.local))?|\.ssh[\\/][^\\/\s\"']+|credentials?\.(?:json|ya?ml|ini|txt)|service[_-]?account[^\\/\s\"']*\.json|id_(?:rsa|ed25519)|[^\\/\s\"']+\.(?:pem|key))"#,
        reason: r#"An interpreter command may expose credential material to model-visible output."#,
        literal_groups: &[&[r#"python"#, r#"py"#, r#"powershell"#, r#"pwsh"#, r#"cmd"#, r#"node"#, r#"ruby"#, r#"perl"#, r#"php"#], &[r#".env"#, r#".ssh"#, r#"credential"#, r#"service"#, r#"id_rsa"#, r#"id_ed25519"#, r#".pem"#, r#".key"#]],
    },
    Rule {
        pattern: r#"(?is)(?:^|[;&|]\s*)sleep\s+\d{2,}(?:\.\d+)?\s*[;&|]"#,
        reason: r#"Polling with a long foreground sleep is blocked. It burns the full duration whether or not the condition is met, cannot react early, and holds the turn open. Use the event-driven path: Monitor with an until-loop to wait on a condition, or run_in_background so completion re-invokes the session. If a fixed settle really is what you want, keep it under ten seconds and do not chain a check onto it."#,
        literal_groups: &[&[r#"sleep"#]],
    },
];
