"""Shared fixtures for connector tests."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def terraform_fixtures_dir():
    return FIXTURES_DIR / "terraform"


@pytest.fixture
def docker_fixtures_dir():
    return FIXTURES_DIR / "docker"


@pytest.fixture
def ansible_fixtures_dir():
    return FIXTURES_DIR / "ansible"


@pytest.fixture
def ci_cd_fixtures_dir():
    return FIXTURES_DIR / "ci_cd"
