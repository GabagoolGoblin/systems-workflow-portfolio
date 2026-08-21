.PHONY: test scan smoke verify

PYTHON := python3 -B

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

scan:
	$(PYTHON) scripts/security_privacy_scan.py

smoke:
	$(PYTHON) scripts/interaction_smoke.py

verify: test scan
