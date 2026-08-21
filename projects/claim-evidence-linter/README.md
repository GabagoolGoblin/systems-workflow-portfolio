# Claim–Evidence Linter

> INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION

A deterministic, local-only Python tool for one narrow governance question: does each declared claim have the exact evidence contract its policy requires? It turns invented claims, typed assertions, and character-accurate citations into `SUPPORTED`, `UNSUPPORTED`, or `NEEDS_REVIEW` without calling a model or network.

## Run in 60 seconds

Requirements: Python 3.11 or newer; no runtime package install.

```bash
make test
make demo
make tamper-demo
```

`make demo` treats the linter's expected findings exit code (`1`) as a successful demonstration. The fixture produces two supported claims, one unsupported claim, and one needing review.

## Five-minute walkthrough

1. Open `demo/synthetic_contract.json` and inspect risk tiers, source minimums, and controlled absolute phrases.
2. Open `demo/synthetic_evidence.json` and match typed assertions to exact source spans.
3. Run `make demo` and trace reason codes and source bindings for each verdict.
4. Run `make tamper-demo` to verify an untouched report, then detect result and input-byte changes.
5. Discuss which upstream judgments remain human-owned: fact identity, stance, source independence, and truth.

## Implemented

- Strict JSON schemas, duplicate-key/non-finite rejection, depth/node/file bounds, and exact cross-reference validation.
- Typed evidence stances, Unicode code-point spans, risk-tier source minimums, and controlled absolute-language policy.
- Stable reason codes, canonical digests, exact report rebuild, non-overwriting mode-`0600` writes, and symlink rejection.
- CLI, tamper demonstration, and 52 standard-library tests.

## Architecture and data flow

The contract and evidence catalog are independently parsed and byte-hashed. Validation binds each citation to an exact assertion and source span. The engine evaluates a fixed decision table. The verifier checks the report self-digest and rebuilds the expected report from the original inputs.

## Verify

```bash
make test
make audit
make demo
make tamper-demo
```

All commands use local synthetic inputs. Report writes require an explicit token and caller-supplied new path.

## Limitations and non-claims

The tool validates a declared contract; it does not establish source truth, semantic entailment, correct stance labels, or genuine source independence. A party controlling both inputs can create a self-consistent fiction. Digests detect drift but do not authenticate an author.

## Provenance

The code, policy fixture, evidence fixture, names, sources, and results are synthetic/original. See [PROVENANCE.md](PROVENANCE.md).

## License scope

Owner-created files are governed only by the repository root `LICENSE`. No external data or asset is bundled.
