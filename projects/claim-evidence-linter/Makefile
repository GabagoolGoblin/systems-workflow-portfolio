.PHONY: test demo tamper-demo audit

PYTHON := python3
ENV := PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src

test:
	$(ENV) $(PYTHON) -B -m unittest discover -s tests -v

demo:
	@status=0; $(ENV) $(PYTHON) -B -m claim_evidence_contract_linter demo || status=$$?; test $$status -eq 1

tamper-demo:
	$(ENV) $(PYTHON) -B tools/tamper_demo.py

audit:
	$(ENV) $(PYTHON) -B tools/audit_project.py
