"""Tests for MlgClient."""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

from mathlore_forge.mlg.client import CheckReport, Diagnostic, MlgClient


class TestMlgClient(unittest.TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.root = Path(self.tmpdir.name).resolve()
        self.client = MlgClient(content_root=self.root, mlg_bin="mlg")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_diagnostic_formatting(self):
        diag_data = {
            "level": "error",
            "message": "Undefined command signature `\\abelian`",
            "origin": "semantic_check",
            "location": {
                "kind": "file",
                "path": "07_algebra/02_groups.mlg",
                "span": {
                    "start": {
                        "line": 42,
                        "column": 5,
                    }
                }
            }
        }
        diag = Diagnostic.from_dict(diag_data)
        formatted = diag.format_line()
        self.assertIn("[ERROR]", formatted)
        self.assertIn("07_algebra/02_groups.mlg:42:5", formatted)
        self.assertIn("\\abelian", formatted)

    def test_check_report_clean_summary(self):
        report = CheckReport(successful=True, issue_count=0, files_checked=3)
        self.assertIn("Clean check: 0 errors across 3 file(s).", report.summary())

    @patch("subprocess.run")
    def test_check_success_parsing(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"successful": true, "issueCount": 0, "filesChecked": 5, "diagnostics": []}'
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        report = self.client.check(paths=["07_algebra/02_groups.mlg"])
        self.assertTrue(report.successful)
        self.assertEqual(report.issue_count, 0)
        self.assertEqual(report.files_checked, 5)

    @patch("subprocess.run")
    def test_check_failure_parsing(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = '''{
            "successful": false,
            "issueCount": 1,
            "filesChecked": 1,
            "diagnostics": [
                {
                    "level": "error",
                    "message": "Unexpected section `suchThat`",
                    "origin": "structural_parser",
                    "location": {
                        "path": "test.mlg",
                        "span": {"start": {"line": 10, "column": 2}}
                    }
                }
            ]
        }'''
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        report = self.client.check(paths=["test.mlg"])
        self.assertFalse(report.successful)
        self.assertEqual(report.issue_count, 1)
        self.assertIn("Unexpected section `suchThat`", report.summary())

    @patch("subprocess.run")
    def test_structure_call(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"title": "Mathlore", "files": []}'
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = self.client.structure(json_output=True)
        self.assertIn("Mathlore", res)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("structure", args)
        self.assertIn("--json", args)


if __name__ == "__main__":
    unittest.main()
