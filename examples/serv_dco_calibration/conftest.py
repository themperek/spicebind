"""Example-local pytest options. Normal runs never touch Docker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parent
REGEN = EXAMPLE / "tools" / "regenerate.py"
RESULTS_CSV = EXAMPLE / "results" / "serv_dco.csv"


def pytest_addoption(parser):
    parser.addoption(
        "--regen-assets",
        action="store_true",
        default=False,
        help="Rebuild generated/ SERV RTL and firmware (may use Docker/Podman)",
    )
    parser.addoption(
        "--check-assets",
        action="store_true",
        default=False,
        help="Regenerate into a temp dir and compare with committed generated/",
    )


def pytest_sessionstart(session):
    regen = getattr(session.config.option, "regen_assets", False)
    check = getattr(session.config.option, "check_assets", False)
    if regen:
        subprocess.check_call([sys.executable, str(REGEN)])
    if check:
        subprocess.check_call([sys.executable, str(REGEN), "--check"])
    if RESULTS_CSV.exists():
        RESULTS_CSV.unlink()
