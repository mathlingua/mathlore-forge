"""Tests for content editor functions."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mathlore_forge.mlg.editor import (
    find_item_by_id,
    insert_item_after_id,
    read_content_file,
    replace_item_by_id,
    resolve_file_path,
    write_content_file,
)

SAMPLE_MLG = """Title: "Algebra Basics"
Id: "id-title-1"


Text: "Overview of groups and monoids."
Id: "id-text-1"


[\\group]
Declares: G ::= (X, *, e)
satisfies:
. forAll: x "in" G
  then: exists: y "in" G suchThat: x * y = e
Documented:
. called: "group"
Id: "id-group-1"


Text: "Closing remarks."
Id: "id-text-2"
"""


class TestEditor(unittest.TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.root = Path(self.tmpdir.name).resolve()
        self.content_dir = self.root / "content" / "07_algebra"
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.content_dir / "02_groups.mlg"
        self.file_path.write_text(SAMPLE_MLG, encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_resolve_file_path_various_forms(self):
        # 1. Full relative path
        p1 = resolve_file_path(self.root, "content/07_algebra/02_groups.mlg")
        self.assertEqual(p1, self.file_path)

        # 2. Relative under content/
        p2 = resolve_file_path(self.root, "07_algebra/02_groups.mlg")
        self.assertEqual(p2, self.file_path)

        # 3. Just filename
        p3 = resolve_file_path(self.root, "02_groups.mlg")
        self.assertEqual(p3, self.file_path)

        # 4. Absolute path
        p4 = resolve_file_path(self.root, self.file_path)
        self.assertEqual(p4, self.file_path)

    def test_read_and_write_content_file(self):
        text = read_content_file(self.root, "07_algebra/02_groups.mlg")
        self.assertIn("Declares: G ::= (X, *, e)", text)

        new_text = text + "\n\nText: \"New Section\"\nId: \"id-new-1\"\n"
        write_content_file(self.root, "07_algebra/02_groups.mlg", new_text)

        read_back = read_content_file(self.root, "07_algebra/02_groups.mlg")
        self.assertIn("id-new-1", read_back)

    def test_find_item_by_id(self):
        item = find_item_by_id(self.root, "id-group-1")
        self.assertIsNotNone(item)
        self.assertEqual(item.id, "id-group-1")
        self.assertIn("[\\group]", item.content)
        self.assertEqual(item.file_path, self.file_path)

        # Quotes should be stripped
        item2 = find_item_by_id(self.root, '"id-group-1"')
        self.assertIsNotNone(item2)
        self.assertEqual(item2.id, "id-group-1")

        # Nonexistent ID
        missing = find_item_by_id(self.root, "non-existent-id")
        self.assertIsNone(missing)

    def test_insert_item_after_id(self):
        new_item = """[\\(abelian)::group]
Refines: G
satisfies:
. forAll: x, y "in" G
  then: x * y = y * x
Documented:
. adjective: "abelian"
"""
        res = insert_item_after_id(
            self.root,
            file_path="02_groups.mlg",
            after_id="id-group-1",
            new_content=new_item,
        )
        self.assertEqual(res.after_id, "id-group-1")

        updated_text = read_content_file(self.root, "02_groups.mlg")
        self.assertIn("[\\(abelian)::group]", updated_text)

        # Check order: id-group-1 should appear before \(abelian)::group, which appears before id-text-2
        idx_group = updated_text.index("Id: \"id-group-1\"")
        idx_abelian = updated_text.index("[\\(abelian)::group]")
        idx_text2 = updated_text.index("Id: \"id-text-2\"")
        self.assertTrue(idx_group < idx_abelian < idx_text2)

    def test_insert_item_at_end_of_file(self):
        new_item = """Text: \"End of Chapter\"
Id: \"id-end-1\""""
        res = insert_item_after_id(
            self.root,
            file_path="02_groups.mlg",
            after_id="id-text-2",
            new_content=new_item,
        )
        updated_text = read_content_file(self.root, "02_groups.mlg")
        self.assertTrue(updated_text.endswith("Id: \"id-end-1\"\n"))

    def test_replace_item_by_id(self):
        replacement = """Text: \"Revised intro text.\"
Id: \"id-text-1\""""
        res = replace_item_by_id(
            self.root,
            file_path="02_groups.mlg",
            item_id="id-text-1",
            new_content=replacement,
        )
        updated_text = read_content_file(self.root, "02_groups.mlg")
        self.assertIn("Revised intro text.", updated_text)
        self.assertNotIn("Overview of groups and monoids.", updated_text)


if __name__ == "__main__":
    unittest.main()
