"""Tests for the Alembic migration setup.

These tests do not require a live PostgreSQL instance: the credential-safety
and script-directory checks only inspect static configuration/metadata, and
the upgrade/downgrade check runs the real `alembic` CLI against a disposable
SQLite database (SQLite is only a stand-in to exercise the migration
machinery end-to-end; it is not used for the application itself).
"""

import os
import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"


def test_alembic_ini_does_not_hardcode_a_database_url() -> None:
    config = Config(str(_ALEMBIC_INI))
    assert config.get_main_option("sqlalchemy.url") in ("", None)
    assert "driver://user:pass@localhost/dbname" not in _ALEMBIC_INI.read_text(
        encoding="utf-8"
    )


def test_initial_revision_exists_and_has_no_parent() -> None:
    config = Config(str(_ALEMBIC_INI))
    script_directory = ScriptDirectory.from_config(config)

    revisions = list(script_directory.walk_revisions())
    initial_revision = next(
        revision for revision in revisions if revision.down_revision is None
    )

    assert initial_revision.revision == "4e6dd0965bd5"


def test_workflow_output_ordering_revision_follows_the_initial_schema() -> None:
    config = Config(str(_ALEMBIC_INI))
    script_directory = ScriptDirectory.from_config(config)

    revision = script_directory.get_revision("7d72d643d597")

    assert revision is not None
    assert revision.down_revision == "4e6dd0965bd5"


def test_target_path_revision_follows_workflow_output_ordering() -> None:
    config = Config(str(_ALEMBIC_INI))
    script_directory = ScriptDirectory.from_config(config)

    revision = script_directory.get_revision("c3a91f2e8b04")

    assert revision is not None
    assert revision.down_revision == "7d72d643d597"
    assert script_directory.get_current_head() == "c3a91f2e8b04"


def test_migration_upgrades_and_downgrades_cleanly(tmp_path: Path) -> None:
    scratch_db = tmp_path / "guardian_ai_migration_check.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{scratch_db}"}

    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert upgrade.returncode == 0, upgrade.stderr

    downgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert downgrade.returncode == 0, downgrade.stderr
