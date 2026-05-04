"""CI/CD connector for GitHub Actions and GitLab CI."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from app.connectors.base import ConnectorResult, IaCConnector
from app.connectors.exceptions import ParseError, PullError
from app.connectors.registry import register

logger = logging.getLogger(__name__)

GITHUB_WORKFLOW_GLOBS = (".github/workflows/*.yml", ".github/workflows/*.yaml")
GITLAB_ROOT_FILES = (".gitlab-ci.yml", ".gitlab-ci.yaml")
GITLAB_RESERVED_KEYS = {
    "stages",
    "variables",
    "default",
    "workflow",
    "include",
    "image",
    "services",
    "before_script",
    "after_script",
    "cache",
}
REGISTRY_RE = re.compile(
    r"\b(?:ghcr\.io|docker\.io|registry\.gitlab\.com|[a-z0-9.-]+\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com)/[^\s\"']+"
)
SSH_TARGET_RE = re.compile(r"\bssh\s+[^\s@]+@([^\s\"']+)")
ARGO_APP_RE = re.compile(r"\bargocd\s+app\s+(?:sync|set)\s+([a-zA-Z0-9_.-]+)")


def _safe_load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", value.strip())
    return slug.strip("_") or "unnamed"


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_github_triggers(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, dict):
        return [str(key) for key in value.keys()]
    return []


def _job_stage_from_name(job_id: str, job: dict[str, Any]) -> tuple[str, bool]:
    explicit_stage = job.get("stage")
    if isinstance(explicit_stage, str) and explicit_stage.strip():
        return explicit_stage.strip(), False

    name = f"{job_id} {job.get('name', '')}".lower()
    if any(token in name for token in ("lint", "ruff", "eslint")):
        return "lint", True
    if any(token in name for token in ("test", "pytest", "integration", "unit")):
        return "test", True
    if any(token in name for token in ("build", "package", "image")):
        return "build", True
    if any(token in name for token in ("release", "publish")):
        return "release", True
    if any(token in name for token in ("deploy", "rollout", "sync")):
        return "deploy", True
    return "job", True


def _normalize_environment(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _collect_script_lines(job: dict[str, Any]) -> list[str]:  # noqa: C901
    lines: list[str] = []

    for step in _ensure_list(job.get("steps")):
        if not isinstance(step, dict):
            continue
        uses = step.get("uses")
        if isinstance(uses, str):
            lines.append(uses)
        run = step.get("run")
        if isinstance(run, str):
            lines.extend(run.splitlines())

    script = job.get("script")
    if isinstance(script, str):
        lines.extend(script.splitlines())
    elif isinstance(script, list):
        for item in script:
            if isinstance(item, str):
                lines.extend(item.splitlines())

    before_script = job.get("before_script")
    if isinstance(before_script, str):
        lines.extend(before_script.splitlines())
    elif isinstance(before_script, list):
        for item in before_script:
            if isinstance(item, str):
                lines.extend(item.splitlines())

    return [line.strip() for line in lines if isinstance(line, str) and line.strip()]


def _infer_targets(script_lines: list[str]) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(target_type: str, identifier: str, relation: str = "deploys_to") -> None:
        key = (target_type, identifier)
        if key in seen:
            return
        seen.add(key)
        targets.append(
            {
                "kind": "ci:deployment_target",
                "name": f"target:{target_type}:{identifier}",
                "target_type": target_type,
                "identifier": identifier,
                "relation_type": relation,
            }
        )

    for line in script_lines:
        for match in REGISTRY_RE.findall(line):
            add("container_registry", match, "publishes_to")

        for host in SSH_TARGET_RE.findall(line):
            add("server", host)

        for app_name in ARGO_APP_RE.findall(line):
            add("argo_application", app_name)

        if "kubectl " in line or "helm " in line or "kustomize " in line:
            add("kubernetes", "cluster")
        if "terraform apply" in line:
            add("terraform_workspace", "default")

    return targets


@register
class CiCdConnector(IaCConnector):
    connector_type = "ci_cd"

    async def pull(self) -> dict[str, Any]:
        source_path = Path(self.url)
        if not source_path.is_dir():
            raise PullError(f"Source path is not a directory: {self.url}")

        github_workflows: list[dict[str, Any]] = []
        for pattern in GITHUB_WORKFLOW_GLOBS:
            for workflow_file in sorted(source_path.glob(pattern)):
                data = _safe_load_yaml(workflow_file)
                if isinstance(data, dict):
                    github_workflows.append(
                        {
                            "path": str(workflow_file.relative_to(source_path)),
                            "data": data,
                        }
                    )

        gitlab_pipelines: list[dict[str, Any]] = []
        visited_gitlab: set[str] = set()
        for filename in GITLAB_ROOT_FILES:
            root_file = source_path / filename
            if root_file.exists():
                gitlab_pipelines.extend(
                    self._load_gitlab_pipeline_tree(source_path, root_file, visited_gitlab)
                )

        if not github_workflows and not gitlab_pipelines:
            raise PullError(
                "No CI/CD definitions found. Expected .github/workflows/* or .gitlab-ci.yml"
            )

        return {
            "github_workflows": github_workflows,
            "gitlab_pipelines": gitlab_pipelines,
        }

    def _load_gitlab_pipeline_tree(
        self, repo_root: Path, path: Path, visited: set[str]
    ) -> list[dict[str, Any]]:
        relative = str(path.relative_to(repo_root))
        if relative in visited:
            return []
        visited.add(relative)

        try:
            data = _safe_load_yaml(path)
        except yaml.YAMLError as exc:
            logger.warning("Failed to parse GitLab pipeline %s: %s", path, exc)
            return []

        if not isinstance(data, dict):
            return []

        items = [{"path": relative, "data": data}]
        include_value = data.get("include")
        for include in _ensure_list(include_value):
            if not isinstance(include, dict):
                continue
            local_path = include.get("local")
            if not isinstance(local_path, str):
                continue
            include_file = repo_root / local_path
            if include_file.exists():
                items.extend(self._load_gitlab_pipeline_tree(repo_root, include_file, visited))
            else:
                logger.warning("Skipping unresolved GitLab local include %s", local_path)
        return items

    async def parse(self, raw_data: dict[str, Any]) -> list[ConnectorResult]:
        try:
            results: dict[tuple[str, str], ConnectorResult] = {}
            self._parse_github(raw_data.get("github_workflows", []), results)
            self._parse_gitlab(raw_data.get("gitlab_pipelines", []), results)
            return list(results.values())
        except Exception as exc:
            raise ParseError(f"Failed to parse CI/CD data: {exc}") from exc

    def _upsert_result(
        self,
        results: dict[tuple[str, str], ConnectorResult],
        *,
        kind: str,
        name: str,
        config_json: dict[str, Any],
        edges: list[dict[str, str]] | None = None,
    ) -> None:
        key = (kind, name)
        incoming_edges = edges or []
        existing = results.get(key)
        if existing is None:
            results[key] = ConnectorResult(
                kind=kind,
                name=name,
                config_json=config_json,
                source_id=self.source_id,
                edges=list(incoming_edges),
            )
            return

        merged_config = dict(existing.config_json)
        merged_config.update(config_json)
        merged_edges = list(existing.edges)
        existing_edge_keys = {(edge["target_name"], edge["relation_type"]) for edge in merged_edges}
        for edge in incoming_edges:
            edge_key = (edge["target_name"], edge["relation_type"])
            if edge_key not in existing_edge_keys:
                merged_edges.append(edge)
                existing_edge_keys.add(edge_key)
        results[key] = ConnectorResult(
            kind=kind,
            name=name,
            config_json=merged_config,
            source_id=self.source_id,
            edges=merged_edges,
        )

    def _parse_github(  # noqa: C901
        self, workflows: list[dict[str, Any]], results: dict[tuple[str, str], ConnectorResult]
    ) -> None:
        for item in workflows:
            path = item["path"]
            data = item["data"]
            workflow_name = f"github:{path}"
            trigger_data = data.get("on", data.get(True))
            triggers = sorted(_extract_github_triggers(trigger_data))
            self._upsert_result(
                results,
                kind="ci:workflow",
                name=workflow_name,
                config_json={
                    "provider": "github_actions",
                    "file_path": path,
                    "name": data.get("name") or Path(path).stem,
                    "triggers": triggers,
                },
            )

            jobs = data.get("jobs", {})
            if not isinstance(jobs, dict):
                continue

            stage_names: list[str] = []
            stage_configs: dict[str, dict[str, Any]] = {}
            for job_id, job in jobs.items():
                if not isinstance(job, dict):
                    continue
                stage_name, inferred = _job_stage_from_name(job_id, job)
                if stage_name not in stage_names:
                    stage_names.append(stage_name)
                    stage_configs[stage_name] = {"provider": "github_actions", "inferred": inferred}

            for position, stage_name in enumerate(stage_names):
                stage_node = f"{workflow_name}:{stage_name}"
                self._upsert_result(
                    results,
                    kind="ci:stage",
                    name=stage_node,
                    config_json={
                        "provider": "github_actions",
                        "workflow": workflow_name,
                        "stage": stage_name,
                        "position": position,
                        **stage_configs[stage_name],
                    },
                )
                self._upsert_result(
                    results,
                    kind="ci:workflow",
                    name=workflow_name,
                    config_json={
                        "provider": "github_actions",
                        "file_path": path,
                        "name": data.get("name") or Path(path).stem,
                        "triggers": triggers,
                    },
                    edges=[{"target_name": stage_node, "relation_type": "contains"}],
                )

            for job_id, job in jobs.items():
                if not isinstance(job, dict):
                    continue
                stage_name, _ = _job_stage_from_name(job_id, job)
                stage_node = f"{workflow_name}:{stage_name}"
                job_node = f"{workflow_name}:{job_id}"
                environment = _normalize_environment(job.get("environment"))
                script_lines = _collect_script_lines(job)
                edges = []
                for need in _ensure_list(job.get("needs")):
                    if isinstance(need, str):
                        edges.append(
                            {
                                "target_name": f"{workflow_name}:{need}",
                                "relation_type": "needs",
                            }
                        )
                if environment:
                    env_node = f"env:{environment}"
                    edges.append({"target_name": env_node, "relation_type": "deploys_to"})
                    self._upsert_result(
                        results,
                        kind="ci:environment",
                        name=env_node,
                        config_json={
                            "provider": "github_actions",
                            "name": environment,
                        },
                    )
                for target in _infer_targets(script_lines):
                    edges.append(
                        {
                            "target_name": target["name"],
                            "relation_type": target["relation_type"],
                        }
                    )
                    self._upsert_result(
                        results,
                        kind=target["kind"],
                        name=target["name"],
                        config_json={
                            "target_type": target["target_type"],
                            "identifier": target["identifier"],
                            "provider": "github_actions",
                            "inferred": True,
                        },
                    )

                self._upsert_result(
                    results,
                    kind="ci:job",
                    name=job_node,
                    config_json={
                        "provider": "github_actions",
                        "workflow": workflow_name,
                        "job_id": job_id,
                        "name": job.get("name") or job_id,
                        "stage": stage_name,
                        "needs": [n for n in _ensure_list(job.get("needs")) if isinstance(n, str)],
                        "runs_on": job.get("runs-on"),
                        "conditions": [job["if"]] if isinstance(job.get("if"), str) else [],
                        "environment": environment,
                        "manual": False,
                    },
                    edges=edges,
                )
                self._upsert_result(
                    results,
                    kind="ci:stage",
                    name=stage_node,
                    config_json={
                        "provider": "github_actions",
                        "workflow": workflow_name,
                        "stage": stage_name,
                    },
                    edges=[{"target_name": job_node, "relation_type": "contains"}],
                )

    def _parse_gitlab(  # noqa: C901
        self, pipelines: list[dict[str, Any]], results: dict[tuple[str, str], ConnectorResult]
    ) -> None:
        for item in pipelines:
            path = item["path"]
            data = item["data"]
            workflow_name = f"gitlab:{path}"
            include_paths = []
            for include in _ensure_list(data.get("include")):
                if isinstance(include, dict) and isinstance(include.get("local"), str):
                    include_paths.append(include["local"])

            stages = [s for s in _ensure_list(data.get("stages")) if isinstance(s, str)]
            self._upsert_result(
                results,
                kind="ci:workflow",
                name=workflow_name,
                config_json={
                    "provider": "gitlab_ci",
                    "file_path": path,
                    "name": Path(path).name,
                    "includes": include_paths,
                },
            )

            jobs = {
                key: value
                for key, value in data.items()
                if isinstance(value, dict) and key not in GITLAB_RESERVED_KEYS
            }

            if not stages:
                inferred_stages: list[str] = []
                for job_id, job in jobs.items():
                    stage_name, _ = _job_stage_from_name(job_id, job)
                    if stage_name not in inferred_stages:
                        inferred_stages.append(stage_name)
                stages = inferred_stages or ["job"]

            for position, stage_name in enumerate(stages):
                stage_node = f"{workflow_name}:{stage_name}"
                self._upsert_result(
                    results,
                    kind="ci:stage",
                    name=stage_node,
                    config_json={
                        "provider": "gitlab_ci",
                        "workflow": workflow_name,
                        "stage": stage_name,
                        "position": position,
                        "inferred": stage_name not in _ensure_list(data.get("stages")),
                    },
                )
                self._upsert_result(
                    results,
                    kind="ci:workflow",
                    name=workflow_name,
                    config_json={
                        "provider": "gitlab_ci",
                        "file_path": path,
                        "name": Path(path).name,
                        "includes": include_paths,
                    },
                    edges=[{"target_name": stage_node, "relation_type": "contains"}],
                )

            for job_id, job in jobs.items():
                stage_name, _ = _job_stage_from_name(job_id, job)
                stage_node = f"{workflow_name}:{stage_name}"
                job_node = f"{workflow_name}:{job_id}"
                environment = _normalize_environment(job.get("environment"))
                script_lines = _collect_script_lines(job)
                edges = []
                for need in _ensure_list(job.get("needs")):
                    if isinstance(need, dict):
                        name = need.get("job")
                    else:
                        name = need
                    if isinstance(name, str):
                        edges.append(
                            {
                                "target_name": f"{workflow_name}:{name}",
                                "relation_type": "needs",
                            }
                        )

                if environment:
                    env_node = f"env:{environment}"
                    edges.append({"target_name": env_node, "relation_type": "deploys_to"})
                    self._upsert_result(
                        results,
                        kind="ci:environment",
                        name=env_node,
                        config_json={
                            "provider": "gitlab_ci",
                            "name": environment,
                        },
                    )

                for target in _infer_targets(script_lines):
                    edges.append(
                        {
                            "target_name": target["name"],
                            "relation_type": target["relation_type"],
                        }
                    )
                    self._upsert_result(
                        results,
                        kind=target["kind"],
                        name=target["name"],
                        config_json={
                            "target_type": target["target_type"],
                            "identifier": target["identifier"],
                            "provider": "gitlab_ci",
                            "inferred": True,
                        },
                    )

                self._upsert_result(
                    results,
                    kind="ci:job",
                    name=job_node,
                    config_json={
                        "provider": "gitlab_ci",
                        "workflow": workflow_name,
                        "job_id": job_id,
                        "name": job.get("name") or job_id,
                        "stage": stage_name,
                        "needs": [
                            need["job"] if isinstance(need, dict) else need
                            for need in _ensure_list(job.get("needs"))
                            if isinstance(need, (str, dict))
                        ],
                        "runs_on": None,
                        "conditions": [str(job.get("rules"))] if job.get("rules") else [],
                        "environment": environment,
                        "manual": job.get("when") == "manual",
                    },
                    edges=edges,
                )
                self._upsert_result(
                    results,
                    kind="ci:stage",
                    name=stage_node,
                    config_json={
                        "provider": "gitlab_ci",
                        "workflow": workflow_name,
                        "stage": stage_name,
                    },
                    edges=[{"target_name": job_node, "relation_type": "contains"}],
                )
