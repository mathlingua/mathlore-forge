"""Tests for configuration management."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mathlore_forge.config import MathloreConfig, load_config


class TestConfig(unittest.TestCase):
    def test_explicit_content_root(self):
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir).resolve()
            cfg = load_config(content_root=tmp_path)
            self.assertEqual(cfg.resolve_content_root(), tmp_path)

    def test_missing_content_root_raises_error(self):
        # Empty config with no mathlore_repo must raise ValueError
        cfg = MathloreConfig()
        with self.assertRaises(ValueError) as ctx:
            cfg.resolve_content_root()
        self.assertIn("explicitly provided", str(ctx.exception))

    def test_skills_dir_resolution(self):
        cfg = load_config()
        skills = cfg.resolve_skills_dir()
        self.assertTrue(skills.is_dir())
        self.assertTrue((skills / "mathlore-author-content").is_dir())

    def test_mlg_bin_resolution(self):
        cfg = load_config()
        mlg = cfg.resolve_mlg_bin()
        self.assertTrue(bool(mlg))


if __name__ == "__main__":
    unittest.main()
