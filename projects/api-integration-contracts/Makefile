.PHONY: artifacts test scan browser screenshots generated verify

PYTHON = PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -B

artifacts:
	$(PYTHON) scripts/build_artifacts.py --confirm SYNTHETIC_ARTIFACTS

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

scan:
	$(PYTHON) scripts/security_privacy_scan.py

browser:
	$(PYTHON) scripts/browser_verify.py

screenshots:
	$(PYTHON) scripts/export_screenshots.py

generated:
	python3 -B ../../tools/release/verify_generated.py --project .

verify: test scan generated browser
