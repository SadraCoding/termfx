.PHONY: build test lint clean
build:           ## build dist/termfx-install.sh (single file for end users)
	./build.sh
test: build      ## smoke-test both the source tree and the built installer
	./tests/smoke.sh ./install.sh
	./tests/smoke.sh dist/termfx-install.sh
lint:            ## needs shellcheck
	shellcheck install.sh lib/*.sh build.sh tests/smoke.sh src/termfx src/init.bash
	python3 -m compileall -q src/termfx-engine src/termfx_engine gen/themes.py lib/rcpatch.py
clean:
	rm -rf dist/* src/__pycache__ gen/__pycache__ lib/__pycache__
