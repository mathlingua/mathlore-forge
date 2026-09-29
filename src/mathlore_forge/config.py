"""Configuration management for Mathlore Forge."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any
from dotenv import find_dotenv, load_dotenv
import yaml
from pydantic import BaseModel, Field


def ensure_env_loaded() -> None:
    """Loads environment variables from .env files if not already loaded."""
    # 1. Search upwards from cwd
    found = find_dotenv(usecwd=True)
    if found:
        load_dotenv(found)

    # 2. Check forge repository root explicitly
    forge_dir = Path(__file__).resolve().parent.parent.parent
    repo_env = forge_dir / ".env"
    if repo_env.is_file():
        load_dotenv(repo_env)

    # 3. Check parent workspace directory
    parent_env = forge_dir.parent / ".env"
    if parent_env.is_file():
        load_dotenv(parent_env)


# Automatically ensure .env variables are loaded upon module import
ensure_env_loaded()


def _resolve_explicit_content_root(hint: str | Path | None = None) -> Path | None:
    """Resolves an explicitly provided content root without searching the filesystem."""
    if hint:
        return Path(hint).resolve()

    env_root = os.getenv("MATHLINGUA_CONTENT_ROOT") or os.getenv("MATHLORE_REPO")
    if env_root:
        return Path(env_root).resolve()

    return None


def _find_mlg_bin(hint: str | Path | None = None) -> str:
    """Locates the `mlg` compiler binary without searching for mathlore content."""
    forge_dir = Path(__file__).resolve().parent.parent.parent

    if hint and hint != "mlg":
        hint_path = Path(hint)
        if hint_path.is_file() and os.access(hint_path, os.X_OK):
            return str(hint_path.resolve())
        rel_path = (forge_dir / hint).resolve()
        if rel_path.is_file() and os.access(rel_path, os.X_OK):
            return str(rel_path)
        which_hint = shutil.which(str(hint))
        if which_hint:
            return which_hint

    env_bin = os.getenv("MLG_BIN")
    if env_bin:
        env_path = Path(env_bin)
        if env_path.is_file() and os.access(env_path, os.X_OK):
            return str(env_path.resolve())
        which_env = shutil.which(env_bin)
        if which_env:
            return which_env

    which_mlg = shutil.which("mlg")
    if which_mlg:
        return which_mlg

    home = Path.home()
    candidates = [
        home / ".local" / "bin" / "mlg",
        forge_dir.parent / "mathlingua" / "target" / "release" / "mlg",
        forge_dir.parent / "mathlingua" / "target" / "debug" / "mlg",
        forge_dir / ".." / "mathlingua" / "target" / "release" / "mlg",
        forge_dir / ".." / "mathlingua" / "target" / "debug" / "mlg",
    ]

    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c.resolve())

    return "mlg"


def _default_skills_dir(hint: str | Path | None = None) -> Path:
    """Returns the skills directory for the Mathlingua agent."""
    if hint:
        return Path(hint).resolve()

    env_skills = os.getenv("MATHLINGUA_SKILLS_DIR")
    if env_skills:
        return Path(env_skills).resolve()

    forge_dir = Path(__file__).resolve().parent.parent.parent
    local_skills = forge_dir / "skills"
    if local_skills.is_dir():
        return local_skills.resolve()

    cwd_skills = Path.cwd() / "skills"
    if cwd_skills.is_dir():
        return cwd_skills.resolve()

    return local_skills.resolve()


class PathsConfig(BaseModel):
    mathlore_repo: str | None = None
    mlg_bin: str = Field(default="mlg")
    skills_dir: str = Field(default="./skills")
    traces_dir: str = Field(default="./traces")
    goldens_dir: str = Field(default="./goldens")
    flywheel_dir: str = Field(default="./flywheel")
    db_path: str = Field(default="mathlore_forge.sqlite")


class ModelsConfig(BaseModel):
    planner: str = Field(default="gemini-3.8-flash")
    author: str = Field(default="gemini-3.8-flash")
    reflection: str = Field(default="gemini-3.8-flash")


class ExecutionConfig(BaseModel):
    mode: str = Field(default="interactive")
    max_iterations: int = Field(default=3)
    serial_authoring: bool = Field(default=True)
    max_compile_retries: int = Field(default=5)


class MathloreConfig(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)

    def resolve_content_root(self) -> Path:
        """Returns the explicitly resolved content root or raises ValueError if not set."""
        root = _resolve_explicit_content_root(self.paths.mathlore_repo)
        if root is None:
            raise ValueError(
                "Content root must be explicitly provided. "
                "The Mathlingua agent does not search the filesystem for the content root. "
                "Please specify `content_root` explicitly or set MATHLINGUA_CONTENT_ROOT."
            )
        return root

    def resolve_mlg_bin(self) -> str:
        """Returns the resolved executable path or binary name for `mlg`."""
        return _find_mlg_bin(self.paths.mlg_bin)

    def resolve_skills_dir(self) -> Path:
        """Returns the resolved path to the skills directory."""
        return _default_skills_dir(self.paths.skills_dir)


def load_config(
    config_path: Path | str | None = None,
    content_root: Path | str | None = None,
    mlg_bin: Path | str | None = None,
    skills_dir: Path | str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> MathloreConfig:
    """Loads Mathlore Forge configuration with optional overrides.

    Args:
        config_path: Optional path to config.yaml.
        content_root: Explicit override for Mathlingua content root.
        mlg_bin: Override for mlg binary.
        skills_dir: Override for skills directory.
        model: Override for author model.
        **kwargs: Additional overrides.
    """
    raw_data: dict[str, Any] = {}

    if config_path is None:
        default_paths = [
            Path.cwd() / "config.yaml",
            Path(__file__).resolve().parent.parent.parent / "config.yaml",
        ]
        for p in default_paths:
            if p.is_file():
                config_path = p
                break

    if config_path and Path(config_path).is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    raw_data = loaded
        except Exception:
            pass

    config = MathloreConfig.model_validate(raw_data)

    if content_root is not None:
        config.paths.mathlore_repo = str(content_root)
    if mlg_bin is not None:
        config.paths.mlg_bin = str(mlg_bin)
    if skills_dir is not None:
        config.paths.skills_dir = str(skills_dir)
    if model is not None:
        config.models.author = model

    return config
