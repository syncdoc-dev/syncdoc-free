"""Git connector: clones/pulls repos and delegates to file-based connectors."""

import logging
import tempfile
from pathlib import Path
from typing import Any

from git import Repo
from git.exc import GitCommandError

from app.connectors.base import ConnectorResult, IaCConnector
from app.connectors.exceptions import PullError
from app.connectors.registry import register

logger = logging.getLogger(__name__)


@register
class GitConnector(IaCConnector):
    connector_type = "git"

    async def pull(self) -> dict[str, Any]:
        """Clone or pull a git repo and scan for IaC files."""
        try:
            tmpdir = tempfile.mkdtemp(prefix="syncdoc-git-")
            repo = Repo.clone_from(self.url, tmpdir, depth=1)
            repo_path = Path(repo.working_dir)
        except GitCommandError as e:
            raise PullError(f"Failed to clone {self.url}: {e}") from e

        result: dict[str, Any] = {
            "repo_path": str(repo_path),
            "terraform_dirs": [],
            "docker_dirs": [],
            "ci_cd_root": None,
        }

        # Find directories containing Terraform files, then keep only the
        # outermost ones.  TerraformConnector uses recursive rglob, so a
        # parent dir already covers all child dirs — scanning both produces
        # duplicate node IDs that cause false drift.
        tf_dirs: set[str] = set()
        for tf_file in repo_path.rglob("*.tf"):
            tf_dirs.add(str(tf_file.parent))
        for tfstate in repo_path.rglob("*.tfstate"):
            tf_dirs.add(str(tfstate.parent))
        sorted_tf_dirs = sorted(tf_dirs)
        result["terraform_dirs"] = [
            d
            for d in sorted_tf_dirs
            if not any(d.startswith(other + "/") for other in sorted_tf_dirs if other != d)
        ]

        # Find directories containing Docker files (no ancestor filtering needed
        # — DockerConnector is not recursive, so dirs don't overlap).
        docker_dirs: set[str] = set()
        for name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            for compose in repo_path.rglob(name):
                docker_dirs.add(str(compose.parent))
        for dockerfile in repo_path.rglob("Dockerfile*"):
            docker_dirs.add(str(dockerfile.parent))
        result["docker_dirs"] = sorted(docker_dirs)

        has_github_workflows = any(repo_path.glob(".github/workflows/*.yml")) or any(
            repo_path.glob(".github/workflows/*.yaml")
        )
        has_gitlab_pipeline = any(
            (repo_path / filename).exists() for filename in (".gitlab-ci.yml", ".gitlab-ci.yaml")
        )
        if has_github_workflows or has_gitlab_pipeline:
            result["ci_cd_root"] = str(repo_path)

        return result

    async def parse(self, raw_data: dict[str, Any]) -> list[ConnectorResult]:
        """Delegate parsing to Terraform, Docker, and CI/CD connectors."""
        from app.connectors.ci_cd import CiCdConnector
        from app.connectors.docker import DockerConnector
        from app.connectors.terraform import TerraformConnector

        results: list[ConnectorResult] = []

        for tf_dir in raw_data.get("terraform_dirs", []):
            tf = TerraformConnector(self.source_id, tf_dir, self.credentials_ref)
            try:
                tf_raw = await tf.pull()
                results.extend(await tf.parse(tf_raw))
            except Exception as e:
                logger.warning("Failed to parse Terraform in %s: %s", tf_dir, e)

        for docker_dir in raw_data.get("docker_dirs", []):
            dc = DockerConnector(self.source_id, docker_dir, self.credentials_ref)
            try:
                dc_raw = await dc.pull()
                results.extend(await dc.parse(dc_raw))
            except Exception as e:
                logger.warning("Failed to parse Docker in %s: %s", docker_dir, e)

        ci_cd_root = raw_data.get("ci_cd_root")
        if ci_cd_root:
            connector = CiCdConnector(self.source_id, ci_cd_root, self.credentials_ref)
            try:
                ci_raw = await connector.pull()
                results.extend(await connector.parse(ci_raw))
            except Exception as e:
                logger.warning("Failed to parse CI/CD in %s: %s", ci_cd_root, e)

        return results
