.PHONY: check compile demo run serve test verify

PYTHON := python3 -B

compile:
	$(PYTHON) -c 'from pathlib import Path; files=sorted(Path("wcag_harness").glob("*.py"))+sorted(Path("tests").glob("*.py")); [compile(p.read_text(encoding="utf-8"), str(p), "exec") for p in files]; print(f"syntax-ok: {len(files)} files")'

test:
	$(PYTHON) -m unittest discover -s tests -v

run:
	$(PYTHON) -m wcag_harness run --manifest fixtures/manifest.json --out build

verify:
	$(PYTHON) -m wcag_harness verify --audit build/audit.json --seal build/audit.sha256

demo: run verify

serve: run
	$(PYTHON) -m wcag_harness demo --serve --open

check: compile test run verify
