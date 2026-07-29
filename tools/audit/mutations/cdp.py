"""Mutations for tools/browser/cdp.py.

The guarantee this file protects is not "the browser is reachable". It is "the
browser we reached is the one we meant". On 2026-07-27 two unrelated Chrome
instances were both listening on port 9224 of this machine, one on IPv4 loopback
with a throwaway profile and one on IPv6 loopback with the automation profile.
Neither reported a conflict, because on Windows those are separate sockets, and
`/json/version` on the hardcoded 127.0.0.1 answered with a valid payload from
the wrong browser.

Every mutation below re-introduces a version of "an endpoint answered, therefore
it is ours", which is the assumption that cost a working browser capability.
"""

TARGET = "tools/browser/cdp.py"
ARGV = ["selftest"]

MUTATIONS = [
    ("identity checking is dropped, so any answer counts as ours",
     "this is the original defect in one line: reachability standing in for "
     "identity, which silently drives a stranger's browser",
     "    verified = [h for h in replied\n"
     "                if listeners.get(_LISTEN_ADDR[h]) in profile_pids]",
     "    verified = replied"),

    ("a stranger on the same port is adopted instead of refused",
     "the refusal is the only thing standing between an automation run and "
     "someone's personal tabs",
     'return None, ("{} answered but the process holding',
     'return replied[0], ("{} answered but the process holding'),

    ("a second browser on the port stops being reported",
     "the run still works, so nobody learns the port is contested until the "
     "next time it resolves the other way",
     'note = ("; WARNING {} also answers on this port and is a DIFFERENT "\n'
     '                    "browser, not this profile".format(", ".join(strangers)))',
     'note = ""'),

    ("an unverified fallback stops labelling itself",
     "on a host with no listener table the resolver is guessing, and a guess "
     "that does not announce itself is indistinguishable from a verified pick",
     '"UNVERIFIED: no listener table, adopted the first answer"',
     '"adopted the first answer"'),

    ("no endpoint at all yields a host anyway",
     "callers treat a returned host as live and go on to build URLs from it",
     '    if not replied:\n        return None, "no debug endpoint answered',
     '    if not replied:\n        return HOST_CANDIDATES[0], "no debug endpoint answered'),

    ("the listener table stops filtering by port",
     "a pid listening on an unrelated port is then credited with this one, so "
     "the identity check passes against the wrong socket",
     "if not lport.isdigit() or int(lport) != port or not pid.isdigit():",
     "if not lport.isdigit() or not pid.isdigit():"),

    ("profile matching stops looking at the command line",
     "every chrome on the box becomes 'ours', which is the same as not checking",
     "if marker in cmd and pid.strip().isdigit():",
     "if pid.strip().isdigit():"),
]
