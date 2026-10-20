"""Synthetic regression tests; no user projects, PDFs, or network are accessed."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTRACT = load("audit_contract")
PDF = load("pdf_text_audit")


class ContractChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="public-skill-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = b'{"run_id":"synthetic-test","value":2}'
        (self.root / "metrics.json").write_bytes(self.source)
        self.prose = "<!-- answer:Q1 -->Synthetic fixture: <!-- result:metric -->2<!-- /result:metric -->.<!-- /answer:Q1 -->"
        (self.root / "answer.md").write_text(self.prose, encoding="utf-8")
        self.contract = {
            "schema_version": "1.0.0",
            "questions": [{"id": "Q1", "prompt": "Report the synthetic fixture value.",
                           "answer_file": "answer.md", "answer_marker": "Q1",
                           "required_result_keys": ["metric"], "from_stage": "paper"}],
            "required_artifacts": [{"path": "metrics.json", "from_stage": "paper"}],
            "results": [{"key": "metric", "source_file": "metrics.json", "pointer": "/value",
                         "format": "integer", "unit": "count", "scope": "synthetic fixture only",
                         "run_id_pointer": "/run_id", "run_id": "synthetic-test",
                         "source_sha256": hashlib.sha256(self.source).hexdigest(), "from_stage": "paper"}],
            "documents": [{"path": "answer.md", "from_stage": "paper", "result_occurrences": {"metric": 1}}],
        }

    def audit(self, contract=None):
        (self.root / "task-contract.json").write_text(json.dumps(
            self.contract if contract is None else contract), encoding="utf-8")
        return CONTRACT.audit(self.root, "paper", "task-contract.json")

    def test_valid_and_read_only(self):
        self.assertEqual(self.audit()[0], "PASS")
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(CONTRACT.audit(self.root, "paper", "task-contract.json")[0], "PASS")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_conflicting_number(self):
        (self.root / "answer.md").write_text(self.prose.replace("-->2<!--", "-->3<!--"), encoding="utf-8")
        self.assertIn("RESULT_TEXT_CONFLICT", " ".join(self.audit()[1]))

    def test_erased_binding(self):
        (self.root / "answer.md").write_text(self.prose.replace("<!-- result:metric -->", "")
                                           .replace("<!-- /result:metric -->", ""), encoding="utf-8")
        self.assertIn("RESULT_OCCURRENCE_CONFLICT", " ".join(self.audit()[1]))

    def test_missing_answer(self):
        (self.root / "answer.md").write_text("", encoding="utf-8")
        self.assertIn("QUESTION_UNANSWERED_OR_AMBIGUOUS", " ".join(self.audit()[1]))

    def test_stale_source(self):
        (self.root / "metrics.json").write_text('{"value":3}', encoding="utf-8")
        self.assertIn("STALE_RESULT_SOURCE", " ".join(self.audit()[1]))

    def test_run_identity(self):
        self.contract["results"][0]["run_id"] = "another-run"
        self.assertIn("RUN_ID_CONFLICT", " ".join(self.audit()[1]))

    def test_schema_rejections(self):
        for mutate in (
            lambda c: c.update(questions=[]),
            lambda c: c["required_artifacts"][0].update(path="../outside.txt"),
            lambda c: c["results"][0].update(format="python:eval(value)"),
            lambda c: c["documents"][0].update(result_occurrences={"metric": True}),
        ):
            value = copy.deepcopy(self.contract)
            mutate(value)
            with self.subTest(contract=value), self.assertRaises(ValueError):
                self.audit(value)

    def test_duplicate_json_keys_and_nonfinite(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1e999}'):
            target = self.root / "bad.json"
            target.write_text(raw, encoding="utf-8")
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                CONTRACT.read_json(target)

    def test_missing_contract_is_not_pass(self):
        self.assertEqual(CONTRACT.audit(self.root, "paper", None)[0], "LEGACY_UNCHECKED")
        with self.assertRaises(ValueError):
            CONTRACT.audit(self.root, "paper", "missing.json")


class PdfChecks(unittest.TestCase):
    def test_normal_text(self):
        for text in ("Why? Which Figure?", "Figure 2 and Eq. (3).", "x = ?, T = 24.",
                     "The variable TBD denotes a duration.", "为什么？见图1与附录A。"):
            with self.subTest(text=text):
                self.assertEqual(PDF.scan_text(text, 1), [])

    def test_known_findings(self):
        for text in ("Figure ??", "Fig.??", "Eq. (??)", "表 ??", "[?]",
                     "Error! Bookmark not defined.", "错误！未找到引用源。",
                     "TODO: finish", "[TBD]", "【待填】"):
            with self.subTest(text=text):
                self.assertTrue(PDF.scan_text(text, 1))

    def test_unreadable(self):
        for text in ("", "12345", "\ufffd", "Text (cid:42)", "Text\x00"):
            with self.subTest(text=text):
                self.assertIsNotNone(PDF.unreadable_reason(text))

    def test_statuses_and_no_output_files(self):
        with tempfile.TemporaryDirectory(prefix="pdf-audit-test-") as directory:
            root = Path(directory)
            pdf = root / "fixture.pdf"
            pdf.write_bytes(b"synthetic non-PDF fixture; extraction is mocked")
            before = pdf.read_bytes()
            for pages, expected in [(["Readable result."], "PASS"), (["Figure ??"], "FAIL"),
                                    ([""], "UNVERIFIED"), (["Readable result.", ""], "UNVERIFIED")]:
                with self.subTest(expected=expected), patch.object(PDF, "extract_pages", return_value=(pages, "mock")):
                    self.assertEqual(PDF.audit(pdf)["status"], expected)
            with patch.object(PDF, "extract_pages", side_effect=RuntimeError("extractor unavailable")):
                self.assertEqual(PDF.audit(pdf)["status"], "UNVERIFIED")
            self.assertEqual(pdf.read_bytes(), before)
            self.assertEqual(list(root.iterdir()), [pdf])


class ManifestChecks(unittest.TestCase):
    def test_valid_and_invalid_manifests(self):
        executable = shutil.which("pwsh")
        self.assertIsNotNone(executable, "PowerShell 7 is required for the release tests")
        with tempfile.TemporaryDirectory(prefix="manifest-audit-test-") as directory:
            root = Path(directory)
            content = b"synthetic result"
            (root / "metric.txt").write_bytes(content)
            (root / "results").mkdir()
            target = root / "results/results-manifest.json"
            stamp = "2026-10-20T00:00:00Z"
            original = {"schema_version": "1.0.0", "frozen_at": stamp, "source_commit": None,
                        "entries": [{"path": "metric.txt", "sha256": hashlib.sha256(content).hexdigest(),
                                     "bytes": len(content), "last_write_utc": stamp}]}
            cases = [("valid", lambda m: None, True),
                     ("empty", lambda m: m.update(entries=[]), False),
                     ("wrong_entries_type", lambda m: m.update(entries=m["entries"][0]), False),
                     ("string_size", lambda m: m["entries"][0].update(bytes=str(len(content))), False),
                     ("boolean_size", lambda m: m["entries"][0].update(bytes=True), False),
                     ("bad_time", lambda m: m.update(frozen_at="invalid"), False),
                     ("bad_commit", lambda m: m.update(source_commit="unknown"), False),
                     ("bad_entry_time", lambda m: m["entries"][0].update(last_write_utc=False), False),
                     ("duplicate", lambda m: m["entries"].append(copy.deepcopy(m["entries"][0])), False),
                     ("outside", lambda m: m["entries"][0].update(path="../outside.txt"), False),
                     ("self_reference", lambda m: m["entries"][0].update(path="results/results-manifest.json"), False),
                     ("wrong_hash", lambda m: m["entries"][0].update(sha256="0" * 64), False),
                     ("missing", lambda m: m["entries"][0].update(path="missing.txt"), False)]
            for name, mutate, success in cases:
                manifest = copy.deepcopy(original)
                mutate(manifest)
                target.write_text(json.dumps(manifest), encoding="utf-8")
                before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                result = subprocess.run([executable, "-NoProfile", "-File",
                                         str(ROOT / "scripts/verify_results.ps1"), "-ProjectRoot", str(root)],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace")
                with self.subTest(name=name):
                    self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
                    if name in ("wrong_hash", "missing"):
                        self.assertIn("VERIFIED_ENTRIES=0", result.stdout)
                    after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
                    self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
