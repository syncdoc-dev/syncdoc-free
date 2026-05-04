"""Repository/source inspection helpers for source validation and UX."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

import yaml
from git import Repo
from git.exc import GitCommandError
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.ansible import NON_PLAYBOOK_FILES, _is_playbook
from app.connectors.docker import COMPOSE_FILENAMES
from app.connectors.exceptions import PullError
from app.models.setting import AppSetting
from app.services.credentials import CredentialManager

_TERRAFORM_LABEL = "Terraform"
_DOCKER_LABEL = "Docker"
_ANSIBLE_LABEL = "Ansible"
_GIT_LABEL = "Git"


@dataclass
class SourceInspectionResult:
    source_type: str
    ok: bool
    summary: str
    matched_files: list[str]
    detected_types: list[str]
    warnings: list[str]


async def inspect_source(source_type: str, url: str, db: AsyncSession) -> SourceInspectionResult:
    local_path, cleanup = await _prepare_source_path(url, db)
    try:
        return _inspect_source_path(source_type, local_path)
    finally:
        cleanup()


async def _prepare_source_path(
    source_url: str, db: AsyncSession
) -> tuple[Path, Callable[[], None]]:
    if not _is_git_url(source_url):
        source_path = Path(source_url)
        if not source_path.is_dir():
            raise PullError(f"Source path is not a directory: {source_url}")
        return source_path, lambda: None

    clone_dir = tempfile.mkdtemp(prefix="syncdoc-inspect-")
    clone_url = source_url

    global_token_row = await db.execute(
        sa_select(AppSetting).where(AppSetting.key == "github_token")
    )
    global_token = global_token_row.scalar_one_or_none()
    if global_token and global_token.value:
        clone_url = CredentialManager.inject_token_in_url(source_url, global_token.value)

    try:
        Repo.clone_from(clone_url, clone_dir, depth=1)
    except GitCommandError as exc:
        shutil.rmtree(clone_dir, ignore_errors=True)
        raise PullError(f"Failed to clone {source_url}: {exc}") from exc

    return Path(clone_dir), lambda: shutil.rmtree(clone_dir, ignore_errors=True)


def _inspect_source_path(source_type: str, source_path: Path) -> SourceInspectionResult:
    terraform_files = _terraform_files(source_path)
    docker_files = _docker_files(source_path)
    ansible_files = _ansible_files(source_path)

    detected: dict[str, list[str]] = {
        "terraform": terraform_files,
        "docker": docker_files,
        "ansible": ansible_files,
    }
    git_files = terraform_files + docker_files + ansible_files
    if git_files:
        detected["git"] = git_files

    matched_files = detected.get(source_type, [])
    ok = len(matched_files) > 0
    detected_types = [key for key, files in detected.items() if files]
    warnings: list[str] = []

    if source_type == "docker" and not docker_files:
        warnings.append(
            "No Docker compose files or Dockerfiles were found anywhere in this repository."
        )
    if source_type == "terraform" and not terraform_files:
        warnings.append("No Terraform `.tf` or `.tfstate` files were found in this repository.")
    if source_type == "ansible" and not ansible_files:
        warnings.append(
            "No Ansible inventory, playbook, role, group_vars, or host_vars files were found."
        )
    if source_type == "git" and not git_files:
        warnings.append("No supported IaC files were found for the Git connector to delegate to.")

    summary = _build_summary(source_type, matched_files, detected)
    return SourceInspectionResult(
        source_type=source_type,
        ok=ok,
        summary=summary,
        matched_files=matched_files[:20],
        detected_types=detected_types,
        warnings=warnings,
    )


def _build_summary(
    source_type: str, matched_files: list[str], detected: dict[str, list[str]]
) -> str:
    label_map = {
        "terraform": _TERRAFORM_LABEL,
        "docker": _DOCKER_LABEL,
        "ansible": _ANSIBLE_LABEL,
        "git": _GIT_LABEL,
    }
    if matched_files:
        return (
            f"Found {len(matched_files)} {label_map.get(source_type, source_type)}-compatible "
            f"files or directories for this source."
        )

    discovered = [
        f"{label_map.get(name, name)} ({len(files)})"
        for name, files in detected.items()
        if name != source_type and files
    ]
    if discovered:
        return (
            f"No {label_map.get(source_type, source_type)} files were found, but this repository "
            f"does contain: {', '.join(discovered)}."
        )
    return (
        f"No {label_map.get(source_type, source_type)}-compatible files were found in this source."
    )


def _terraform_files(source_path: Path) -> list[str]:
    files = {
        str(path.relative_to(source_path))
        for pattern in ("*.tf", "*.tfstate")
        for path in source_path.rglob(pattern)
    }
    return sorted(files)


def _docker_files(source_path: Path) -> list[str]:
    files: set[str] = set()
    for name in COMPOSE_FILENAMES:
        files.update(str(path.relative_to(source_path)) for path in source_path.rglob(name))
    files.update(str(path.relative_to(source_path)) for path in source_path.rglob("Dockerfile*"))
    return sorted(files)


def _ansible_files(source_path: Path) -> list[str]:  # noqa: C901
    files: set[str] = set()

    for path in source_path.rglob("*"):
        if not path.is_file():
            continue
        rel = PurePosixPath(path.relative_to(source_path).as_posix())
        in_inventory_dir = "inventory" in rel.parts[:-1]
        if path.name in {"inventory.yml", "inventory.yaml", "hosts.yml", "hosts.yaml"} and (
            in_inventory_dir or len(rel.parts) == 1
        ):
            files.add(str(rel))
        if (
            path.name in {"inventory", "hosts"}
            and not path.suffix
            and (in_inventory_dir or len(rel.parts) == 1)
        ):
            files.add(str(rel))

    for path in list(source_path.rglob("*.yml")) + list(source_path.rglob("*.yaml")):
        if not path.is_file() or path.name in NON_PLAYBOOK_FILES:
            continue
        rel = PurePosixPath(path.relative_to(source_path).as_posix())
        if {"roles", "group_vars", "host_vars"} & set(rel.parts):
            continue
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if isinstance(data, list) and data and _is_playbook(data):
            files.add(str(rel))

    for dir_name in ("roles", "group_vars", "host_vars"):
        for path in source_path.rglob(dir_name):
            if path.is_dir():
                files.add(str(path.relative_to(source_path)))

    return sorted(files)


def _is_git_url(url: str) -> bool:
    return url.startswith(("https://", "http://", "git://", "ssh://", "git@"))
