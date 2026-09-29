"""Tests for MathlinguaToolkit."""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

from mathlore_forge.tools.mathlingua_tools import MathlinguaToolkit

SAMPLE_CONTENT = """Title: "Test Page"
Id: "id-page-1"


[\\group]
Declares: G
Id: "id-group-1"
"""


class TestTools(unittest.TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.root = Path(self.tmpdir.name).resolve()
        self.test_file = self.root / "content" / "test.mlg"
        self.test_file.parent.mkdir(parents=True, exist_ok=True)
        self.test_file.write_text(SAMPLE_CONTENT, encoding="utf-8")
        self.toolkit = MathlinguaToolkit(content_root=self.root, mlg_bin="mlg")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_get_tools_list(self):
        tools = self.toolkit.get_tools()
        names = [t.__name__ for t in tools]
        expected = [
            "run_mlg",
            "mlg_check",
            "mlg_structure",
            "mlg_search",
            "mlg_format",
            "read_content_file",
            "write_content_file",
            "insert_item_after",
            "find_item_by_id",
            "replace_item_by_id",
        ]
        for exp in expected:
            self.assertIn(exp, names)

    def test_file_read_and_write_tools(self):
        read_res = self.toolkit.read_content_file("test.mlg")
        self.assertIn("[\\group]", read_res)

        write_res = self.toolkit.write_content_file("new_file.mlg", "Title: \"New\"\nId: \"id-new\"\n")
        self.assertIn("Successfully wrote", write_res)
        self.assertTrue((self.root / "content" / "new_file.mlg").is_file() or (self.root / "new_file.mlg").is_file())

    def test_insert_item_after_tool(self):
        new_item = """[\\monoid]
Declares: M
Documented:
. called: "monoid"
"""
        res = self.toolkit.insert_item_after(
            file_path="test.mlg",
            after_id="id-group-1",
            new_item_content=new_item,
        )
        self.assertIn("Successfully inserted", res)
        self.assertIn("id-group-1", res)

        content = self.toolkit.read_content_file("test.mlg")
        self.assertIn("[\\monoid]", content)

    def test_find_and_replace_item_tools(self):
        find_res = self.toolkit.find_item_by_id("id-group-1")
        self.assertIn("Found item 'id-group-1'", find_res)
        self.assertIn("[\\group]", find_res)

        replace_res = self.toolkit.replace_item_by_id(
            file_path="test.mlg",
            item_id="id-group-1",
            new_item_content="[\\group]\nDeclares: G ::= (X, *)\nId: \"id-group-1\"",
        )
        self.assertIn("Successfully replaced", replace_res)
        updated = self.toolkit.read_content_file("test.mlg")
        self.assertIn("G ::= (X, *)", updated)

    @patch.object(MathlinguaToolkit, "run_mlg")
    def test_run_mlg_tool(self, mock_run_mlg):
        mock_run_mlg.return_value = "mlg 1.0.0"
        res = self.toolkit.run_mlg("version")
        self.assertEqual(res, "mlg 1.0.0")


if __name__ == "__main__":
    unittest.main()
