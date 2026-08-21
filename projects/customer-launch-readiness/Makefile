.PHONY: scan browser test verify

PYTHON = PYTHONDONTWRITEBYTECODE=1 python3 -B

scan:
	$(PYTHON) scripts/security_privacy_scan.py

browser:
	$(PYTHON) scripts/interaction_smoke.py

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

verify: scan test
