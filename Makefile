.PHONY: policy unit scans generated browser verify manifest clean

PYTHON := python3 -E -B
PYTHON_PROJECT_PATH := python3 -B

policy:
	$(PYTHON) tools/release/verify_inventory.py --check release-inventory.json
	$(PYTHON) tools/release/publication_scan.py --self-test --policy release-policy.json .
	$(PYTHON) tools/release/verify_links.py --root .
	$(PYTHON) tools/release/verify_manifest.py RELEASE_MANIFEST.sha256

unit:
	cd projects/catalog-lifecycle && $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	cd projects/interface-contract-harness && $(PYTHON) -m unittest discover -s tests -v
	cd projects/claim-evidence-linter && PYTHONPATH=src $(PYTHON_PROJECT_PATH) -m unittest discover -s tests -v
	cd projects/bulk-price-control && $(PYTHON) -m unittest discover -s tests -v
	cd projects/catalog-migration-validator && $(PYTHON) -m unittest discover -s tests -v
	cd projects/api-integration-contracts && $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	cd projects/ai-evaluation-release-gates && $(PYTHON) -m unittest discover -s tests -v
	cd projects/implementation-readiness && $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	cd projects/public-product-validation && $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	cd projects/support-triage-workbench && $(PYTHON) -m unittest discover -s tests -v
	cd projects/human-in-the-loop-control && $(PYTHON) -m unittest discover -s demos/hitl-desktop -p 'test_*.py' -v
	cd projects/customer-launch-readiness && $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

scans:
	cd projects/claim-evidence-linter && PYTHONPATH=src $(PYTHON_PROJECT_PATH) tools/audit_project.py
	cd projects/api-integration-contracts && $(PYTHON) scripts/security_privacy_scan.py
	cd projects/ai-evaluation-release-gates && $(PYTHON) scripts/security_privacy_scan.py
	cd projects/implementation-readiness && $(PYTHON) scripts/security_privacy_scan.py
	cd projects/customer-launch-readiness && $(PYTHON) scripts/security_privacy_scan.py
	cd projects/support-triage-workbench && $(PYTHON) tools/publication_scan.py

generated:
	$(PYTHON) tools/release/verify_generated.py --root .
	$(PYTHON) tools/release/verify_generated.py --project projects/interface-contract-harness
	$(PYTHON) tools/release/verify_generated.py --project projects/api-integration-contracts
	$(PYTHON) tools/release/verify_generated.py --project projects/ai-evaluation-release-gates
	$(PYTHON) tools/release/verify_generated.py --project projects/public-product-validation

browser:
	$(PYTHON) tools/release/verify_landing.py
	$(PYTHON) tools/release/static_demo_smoke.py projects/catalog-lifecycle/index.html
	$(PYTHON) tools/release/static_demo_smoke.py projects/public-product-validation/index.html --allow-click-domain world.openfoodfacts.org --allow-click-domain openfoodfacts.github.io --allow-click-domain opendatacommons.org
	cd projects/api-integration-contracts && $(PYTHON) scripts/browser_verify.py
	cd projects/ai-evaluation-release-gates && $(PYTHON) scripts/interaction_smoke.py
	cd projects/implementation-readiness && $(PYTHON) scripts/interaction_smoke.py
	cd projects/customer-launch-readiness && $(PYTHON) scripts/interaction_smoke.py
	task_temp=$$(mktemp -d); trap 'if test -f "$$task_temp/hitl-smoke.log"; then unlink "$$task_temp/hitl-smoke.log"; fi; rmdir "$$task_temp"' EXIT; if command -v xvfb-run >/dev/null 2>&1; then gui_prefix='xvfb-run -a'; elif test -n "$$DISPLAY"; then gui_prefix=''; else echo 'FAIL: xvfb-run or DISPLAY required' >&2; exit 1; fi; $$gui_prefix $(PYTHON) projects/human-in-the-loop-control/demos/hitl-desktop/smoke_test.py --log-path "$$task_temp/hitl-smoke.log" && test -s "$$task_temp/hitl-smoke.log"

verify:
	$(PYTHON) tools/release/verify_all.py --browser

manifest:
	$(PYTHON) tools/release/build_manifest.py RELEASE_MANIFEST.sha256

clean:
	$(PYTHON) tools/release/publication_scan.py --policy release-policy.json .
