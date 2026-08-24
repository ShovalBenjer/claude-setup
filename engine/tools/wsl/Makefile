# Entry point for WSL work. The Makefile is the menu; bootstrap.sh is the privileged
# step, and it asks for sudo exactly once.
#
#   make -f tools/wsl/Makefile bootstrap
#
# Why targets and not a README of commands: a README is a claim about what works and
# nothing checks it. A target either runs or it does not.

REPO ?= $(HOME)/claude-setup
PY   ?= python3

.DEFAULT_GOAL := help
.PHONY: help bootstrap check gate test clone doctor

help:
	@echo "targets:"
	@echo "  bootstrap  install everything WSL is missing. ONE sudo prompt."
	@echo "  doctor     report what is present or missing. No sudo, no writes."
	@echo "  clone      stage a clone of the Windows repo into ext4"
	@echo "  check      codemap + docmap + slop lint"
	@echo "  gate       full 12-domain gate run"
	@echo "  test       pytest"

bootstrap:
	bash $(CURDIR)/bootstrap.sh

# Deliberately separate from bootstrap and deliberately unprivileged: knowing what is
# missing should never cost a password.
doctor:
	@for t in git python $(PY) pip3 pytest uv gh rg fd cargo rustc node claude; do \
		printf '  %-8s ' $$t; \
		command -v $$t >/dev/null 2>&1 && $$t --version 2>&1 | head -1 | cut -c1-46 || echo MISSING; \
	done
	@echo "  repo: $(REPO)"; test -d $(REPO) && echo "  repo present" || echo "  repo ABSENT"

# --no-hardlinks because the source is on /mnt/c and the destination is ext4; hardlinks
# across that boundary are not possible and git falls back silently, which hides how
# long the copy really took.
clone:
	git clone --no-hardlinks /mnt/c/Users/shova/claude-setup $(REPO)

check:
	cd $(REPO) && $(PY) tools/map/codemap.py check
	cd $(REPO) && $(PY) tools/docmap/docmap.py check

gate:
	cd $(REPO) && $(PY) tools/gate/gate.py run --project .

test:
	cd $(REPO) && $(PY) -m pytest tests/ -q
