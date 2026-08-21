from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path

from claim_evidence_contract_linter.errors import InputError, LocalIOError
from claim_evidence_contract_linter.local_io import (
    MAX_INPUT_BYTES,
    decode_json_bytes,
    read_regular_file,
    write_new_private_file,
)
from claim_evidence_contract_linter.validation import (
    validate_contract,
    validate_cross_references,
    validate_evidence,
)

from support import mutable_fixtures


class JsonAndSchemaTests(unittest.TestCase):
    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(InputError, "duplicate JSON object key"):
            decode_json_bytes(b'{"a": 1, "a": 2}', label="test")

    def test_nan_rejected(self):
        with self.assertRaisesRegex(InputError, "non-finite"):
            decode_json_bytes(b'{"a": NaN}', label="test")

    def test_invalid_utf8_rejected(self):
        with self.assertRaisesRegex(InputError, "UTF-8"):
            decode_json_bytes(b"\xff", label="test")

    def test_lone_unicode_surrogate_rejected_by_schema(self):
        contract, _cb, _evidence, _eb = mutable_fixtures()
        contract["claims"][0]["text"] = "bad surrogate: \ud800"
        with self.assertRaisesRegex(InputError, "no lone surrogates"):
            validate_contract(contract)

    def test_excessive_json_nesting_fails_as_input_error(self):
        nested = (b"[" * 2_000) + (b"]" * 2_000)
        with self.assertRaisesRegex(InputError, "maximum depth"):
            decode_json_bytes(nested, label="test")

    def test_unknown_contract_key_rejected(self):
        contract, _cb, _evidence, _eb = mutable_fixtures()
        contract["silent_override"] = True
        with self.assertRaisesRegex(InputError, "unknown keys"):
            validate_contract(contract)

    def test_missing_policy_key_rejected(self):
        contract, _cb, _evidence, _eb = mutable_fixtures()
        del contract["policy"]["minimum_distinct_sources"]
        with self.assertRaisesRegex(InputError, "missing keys"):
            validate_contract(contract)

    def test_boolean_span_rejected(self):
        _contract, _cb, evidence, _eb = mutable_fixtures()
        evidence["sources"][0]["assertions"][0]["start"] = False
        with self.assertRaisesRegex(InputError, "booleans are not accepted"):
            validate_evidence(evidence)

    def test_out_of_range_span_rejected(self):
        _contract, _cb, evidence, _eb = mutable_fixtures()
        evidence["sources"][0]["assertions"][0]["end"] = 999
        with self.assertRaisesRegex(InputError, "exceeds source content"):
            validate_evidence(evidence)

    def test_assertion_quote_mismatch_rejected(self):
        _contract, _cb, evidence, _eb = mutable_fixtures()
        evidence["sources"][0]["assertions"][0]["quote"] = "invented mismatch"
        with self.assertRaisesRegex(InputError, "does not exactly match"):
            validate_evidence(evidence)

    def test_duplicate_claim_id_rejected(self):
        contract, _cb, _evidence, _eb = mutable_fixtures()
        duplicate = copy.deepcopy(contract["claims"][0])
        contract["claims"].append(duplicate)
        with self.assertRaisesRegex(InputError, "duplicate identifier"):
            validate_contract(contract)

    def test_duplicate_assertion_id_within_source_rejected(self):
        _contract, _cb, evidence, _eb = mutable_fixtures()
        duplicate = copy.deepcopy(evidence["sources"][0]["assertions"][0])
        evidence["sources"][0]["assertions"].append(duplicate)
        with self.assertRaisesRegex(InputError, "duplicate identifier"):
            validate_evidence(evidence)

    def test_duplicate_citation_rejected(self):
        contract, _cb, _evidence, _eb = mutable_fixtures()
        contract["claims"][0]["citations"].append(
            copy.deepcopy(contract["claims"][0]["citations"][0])
        )
        with self.assertRaisesRegex(InputError, "duplicate source/assertion"):
            validate_contract(contract)

    def test_unknown_stance_rejected(self):
        _contract, _cb, evidence, _eb = mutable_fixtures()
        evidence["sources"][0]["assertions"][0]["stance"] = "maybe"
        with self.assertRaisesRegex(InputError, "must be one of"):
            validate_evidence(evidence)

    def test_unknown_source_reference_rejected(self):
        contract, _cb, evidence, _eb = mutable_fixtures()
        contract["claims"][0]["citations"][0]["source_id"] = "missing-source"
        with self.assertRaisesRegex(InputError, "unknown source"):
            validate_cross_references(
                validate_contract(contract), validate_evidence(evidence)
            )

    def test_unknown_assertion_reference_rejected(self):
        contract, _cb, evidence, _eb = mutable_fixtures()
        contract["claims"][0]["citations"][0]["assertion_id"] = "missing-assertion"
        with self.assertRaisesRegex(InputError, "unknown assertion"):
            validate_cross_references(
                validate_contract(contract), validate_evidence(evidence)
            )

    def test_non_lowercase_absolute_term_rejected(self):
        contract, _cb, _evidence, _eb = mutable_fixtures()
        contract["policy"]["absolute_terms"].append("Always")
        with self.assertRaisesRegex(InputError, "case-folded"):
            validate_contract(contract)


class SafeLocalIOTests(unittest.TestCase):
    def test_oversize_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.json"
            path.write_bytes(b"x" * (MAX_INPUT_BYTES + 1))
            with self.assertRaisesRegex(InputError, "exceeds"):
                read_regular_file(path)

    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            link = Path(directory) / "link.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaisesRegex(LocalIOError, "cannot safely open"):
                read_regular_file(link)

    def test_new_output_is_mode_0600(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            write_new_private_file(path, b"{}\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.read_bytes(), b"{}\n")

    def test_output_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_bytes(b"original")
            with self.assertRaisesRegex(LocalIOError, "refusing"):
                write_new_private_file(path, b"replacement")
            self.assertEqual(path.read_bytes(), b"original")

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_output_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            link = Path(directory) / "link.json"
            target.write_bytes(b"original")
            link.symlink_to(target)
            with self.assertRaisesRegex(LocalIOError, "refusing"):
                write_new_private_file(link, b"replacement")
            self.assertEqual(target.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
