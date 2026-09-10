"""Configuration management for Mathlore Forge."""

from pathlib import Path
import os
import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class PathsConfig(BaseModel):
    mathlore_repo: Path = Field(default=Path("../../mathlore"))
    mlg_bin: Path = Field(default=Path("../../mathlingua/target/release/mlg"))
    skills_dir: Path = Field(default=Path("./skills"))
    traces_dir: Path = Field(default=Path("./traces"))
    goldens_dir: Path = Field(default=Path("./goldens"))
    flywheel_dir: Path = Field(default=Path("./flywheel"))
    db_path: str = Field(default="mathlore_forge.sqlite")


class ModelsConfig(BaseModel):
    planner: str = Field(default="gemini-3.8-flash")
    author: str = Field(default="gemini-3.8-flash")
    reflection: str = Field(default="gemini-3.8-flash")


class ExecutionConfig(BaseModel):
    mode: str = Field(default="interactive")  # "interactive" or "auto"
    max_iterations: int = Field(default=3)
    serial_authoring: bool = Field(default=True)
    max_compile_retries: int = Field(default=5)


class GuardrailsConfig(BaseModel):
    enforce_citations: bool = Field(default=True)
    reputable_sources: list[str] = Field(default_factory=lambda: [
        "textbook", "peer-reviewed paper", "nlab", "stanford encyclopedia of philosophy", "mathworld"
    ])
    flag_mathlingua_gaps: bool = Field(default=True)


class TelemetryConfig(BaseModel):
    enable_console_summary: bool = Field(default=True)
    enable_file_exporter: bool = Field(default=True)
    traces_dir: Path = Field(default=Path("./traces"))
    otlp_endpoint: str | None = Field(default=None)


class AppConfig(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    gemini_api_key: str | None = Field(default=None)
    dbos_system_database_url: str | None = Field(default=None)

    @classmethod
    def load(cls, config_path: Path | str | None = None) -> "AppConfig":
        config_data = {}
        target_path = Path(config_path) if config_path else Path("config.yaml")
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    config_data = loaded

        config = cls(**config_data)

        # Environment variable overrides
        if api_key := os.environ.get("GEMINI_API_KEY"):
            config.gemini_api_key = api_key

        if repo_path := os.environ.get("MATHLORE_REPO_PATH"):
            config.paths.mathlore_repo = Path(repo_path)

        if mlg_path := os.environ.get("MLG_BIN_PATH"):
            config.paths.mlg_bin = Path(mlg_path)
        elif not config.paths.mlg_bin.exists():
            # Fallback to debug binary if release doesn't exist
            debug_path = config.paths.mlg_bin.parent.parent / "debug" / "mlg"
            if debug_path.exists():
                config.paths.mlg_bin = debug_path

        if db_url := os.environ.get("DBOS_SYSTEM_DATABASE_URL"):
            config.dbos_system_database_url = db_url
        else:
            config.dbos_system_database_url = f"sqlite:///{config.paths.db_path}"

        if otlp := os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
            config.telemetry.otlp_endpoint = otlp

        # Resolve paths relative to working directory or mathlore-forge root
        config.paths.mathlore_repo = config.paths.mathlore_repo.resolve()
        if config.paths.mlg_bin.exists():
            config.paths.mlg_bin = config.paths.mlg_bin.resolve()

        config.paths.traces_dir.mkdir(parents=True, exist_ok=True)
        config.paths.goldens_dir.mkdir(parents=True, exist_ok=True)
        config.paths.flywheel_dir.mkdir(parents=True, exist_ok=True)

        return config
