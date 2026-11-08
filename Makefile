.PHONY: test lint syntax clean help

help:            ## list targets
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

syntax:          ## bash -n and byte-compile everything (no extra tools needed)
	for f in install.sh lib/*.sh src/termfx src/termfx.d/*.sh src/init.bash tests/smoke.sh; do bash -n $$f || exit 1; done
	python3 -m compileall -q src/termfx-engine src/termfx_engine gen/themes.py lib/rcpatch.py tests

lint: syntax     ## syntax + shellcheck (needs shellcheck)
	shellcheck -x install.sh lib/*.sh tests/smoke.sh src/termfx src/termfx.d/*.sh src/init.bash

test: syntax     ## layout + real-shell session tests, smoke-test installer
	python3 tests/layout_test.py
	python3 tests/session_test.py bash
	python3 tests/overlap_test.py bash
	./tests/smoke.sh ./install.sh

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
