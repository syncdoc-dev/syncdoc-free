"""Ansible connector: parses inventory files and playbooks."""

import logging
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from app.connectors.base import ConnectorResult, IaCConnector
from app.connectors.exceptions import ParseError, PullError
from app.connectors.registry import register

logger = logging.getLogger(__name__)

INVENTORY_FILENAMES = {"inventory.yml", "inventory.yaml", "hosts.yml", "hosts.yaml"}

PLAYBOOK_GLOBS = ["*.yml", "*.yaml"]

# Files that are definitely not playbooks
NON_PLAYBOOK_FILES = {
    "requirements.yml",
    "requirements.yaml",
    "galaxy.yml",
    "galaxy.yaml",
    "ansible.cfg",
    "inventory.yml",
    "inventory.yaml",
    "hosts.yml",
    "hosts.yaml",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}


@register
class AnsibleConnector(IaCConnector):
    connector_type = "ansible"

    async def pull(self) -> dict[str, Any]:
        """Read Ansible inventory and playbook files from the source directory."""
        source_path = Path(self.url)
        if not source_path.is_dir():
            raise PullError(f"Source path is not a directory: {self.url}")

        return {
            "inventory": self._pull_inventory(source_path),
            "playbooks": _pull_playbooks(source_path),
            "roles": _pull_roles(source_path),
            "group_vars": _pull_recursive_vars(source_path, "group_vars"),
            "host_vars": _pull_recursive_vars(source_path, "host_vars"),
        }

    @staticmethod
    def _pull_inventory(source_path: Path) -> list:  # noqa: C901
        """Pull YAML and INI inventory files."""
        inventory: list = []
        for inv_file in sorted(source_path.rglob("*")):
            if not inv_file.is_file():
                continue
            path_parts = PurePosixPath(inv_file.relative_to(source_path).as_posix()).parts
            in_inventory_dir = "inventory" in path_parts[:-1]
            if inv_file.name in INVENTORY_FILENAMES and (in_inventory_dir or len(path_parts) == 1):
                try:
                    data = yaml.safe_load(inv_file.read_text())
                    if data:
                        inventory.append(data)
                except yaml.YAMLError as e:
                    logger.warning("Failed to parse inventory %s: %s", inv_file, e)

        for ini_file in sorted(source_path.rglob("*")):
            if not ini_file.is_file() or ini_file.suffix:
                continue
            path_parts = PurePosixPath(ini_file.relative_to(source_path).as_posix()).parts
            in_inventory_dir = "inventory" in path_parts[:-1]
            if ini_file.name in {"inventory", "hosts"} and (
                in_inventory_dir or len(path_parts) == 1
            ):
                try:
                    parsed = _parse_ini_inventory(ini_file.read_text())
                    if parsed:
                        inventory.append(parsed)
                except Exception as e:
                    logger.warning(
                        "Failed to parse INI inventory %s: %s",
                        ini_file,
                        e,
                    )
        return inventory

    async def parse(self, raw_data: dict[str, Any]) -> list[ConnectorResult]:
        """Transform Ansible data into ConnectorResult objects."""
        try:
            results: list[ConnectorResult] = []
            results.extend(self._parse_inventory(raw_data))
            results.extend(self._parse_playbooks(raw_data))
            results.extend(self._parse_roles(raw_data))
            results.extend(self._parse_vars(raw_data))
        except Exception as e:
            raise ParseError(f"Failed to parse Ansible data: {e}") from e
        return results

    def _parse_inventory(self, raw_data: dict) -> list[ConnectorResult]:
        """Parse inventory into host and group nodes."""
        results: list[ConnectorResult] = []
        seen_hosts: set[str] = set()
        seen_groups: set[str] = set()

        for inventory in raw_data.get("inventory", []):
            self._walk_inventory_group(inventory, results, seen_hosts, seen_groups)

        return results

    def _walk_inventory_group(
        self,
        data: dict,
        results: list[ConnectorResult],
        seen_hosts: set[str],
        seen_groups: set[str],
        parent_group: str | None = None,
    ) -> None:
        """Recursively walk YAML inventory structure."""
        for group_name, group_data in data.items():
            if group_name in seen_groups:
                continue
            if not isinstance(group_data, dict):
                continue

            seen_groups.add(group_name)
            edges: list[dict[str, str]] = []
            if parent_group:
                edges.append({"target_name": parent_group, "relation_type": "child_of"})

            results.append(
                ConnectorResult(
                    kind="ansible:group",
                    name=group_name,
                    config_json={"vars": group_data.get("vars", {})},
                    source_id=self.source_id,
                    edges=edges,
                )
            )

            # Parse hosts in this group
            hosts = group_data.get("hosts", {})
            if isinstance(hosts, dict):
                for host_name, host_vars in hosts.items():
                    if host_name not in seen_hosts:
                        seen_hosts.add(host_name)
                        results.append(
                            ConnectorResult(
                                kind="ansible:host",
                                name=host_name,
                                config_json=host_vars or {},
                                source_id=self.source_id,
                                edges=[{"target_name": group_name, "relation_type": "member_of"}],
                            )
                        )

            # Recurse into children
            children = group_data.get("children", {})
            if isinstance(children, dict):
                self._walk_inventory_group(
                    children,
                    results,
                    seen_hosts,
                    seen_groups,
                    parent_group=group_name,
                )

    def _parse_playbooks(self, raw_data: dict) -> list[ConnectorResult]:
        """Parse playbooks into play nodes with role/task edges."""
        results: list[ConnectorResult] = []

        for pb in raw_data.get("playbooks", []):
            pb_name = pb["name"]
            plays = pb.get("plays", [])
            edges: list[dict[str, str]] = []

            for play in plays:
                if not isinstance(play, dict):
                    continue

                # Link to target hosts/groups
                hosts = play.get("hosts", "")
                if isinstance(hosts, str):
                    for host in hosts.split(","):
                        host = host.strip()
                        if host:
                            edges.append({"target_name": host, "relation_type": "targets"})

                # Link to roles used
                for role in play.get("roles", []):
                    role_name = (
                        role if isinstance(role, str) else role.get("role", role.get("name", ""))
                    )
                    if role_name:
                        edges.append({"target_name": role_name, "relation_type": "uses_role"})

            config = {
                "path": pb.get("path", ""),
                "play_count": len(plays),
                "hosts": sorted(
                    {e["target_name"] for e in edges if e["relation_type"] == "targets"}
                ),
                "roles": sorted(
                    {e["target_name"] for e in edges if e["relation_type"] == "uses_role"}
                ),
            }

            results.append(
                ConnectorResult(
                    kind="ansible:playbook",
                    name=pb_name,
                    config_json=config,
                    source_id=self.source_id,
                    edges=edges,
                )
            )

        return results

    def _parse_roles(self, raw_data: dict) -> list[ConnectorResult]:
        """Parse roles into role nodes."""
        results: list[ConnectorResult] = []

        for role in raw_data.get("roles", []):
            config = {
                "path": role.get("path", ""),
                "dependencies": role.get("dependencies", []),
                "has_tasks": role.get("has_tasks", False),
                "has_handlers": role.get("has_handlers", False),
                "has_templates": role.get("has_templates", False),
                "has_defaults": role.get("has_defaults", False),
            }

            edges: list[dict[str, str]] = []
            for dep in role.get("dependencies", []):
                dep_name = dep if isinstance(dep, str) else dep.get("role", dep.get("name", ""))
                if dep_name:
                    edges.append({"target_name": dep_name, "relation_type": "depends_on"})

            results.append(
                ConnectorResult(
                    kind="ansible:role",
                    name=role["name"],
                    config_json=config,
                    source_id=self.source_id,
                    edges=edges,
                )
            )

        return results

    def _parse_vars(self, raw_data: dict) -> list[ConnectorResult]:
        """Parse group_vars and host_vars into variable nodes."""
        results: list[ConnectorResult] = []

        for group_name, vars_data in raw_data.get("group_vars", {}).items():
            results.append(
                ConnectorResult(
                    kind="ansible:group_vars",
                    name=group_name,
                    config_json=vars_data,
                    source_id=self.source_id,
                    edges=[{"target_name": group_name, "relation_type": "configures"}],
                )
            )

        for host_name, vars_data in raw_data.get("host_vars", {}).items():
            results.append(
                ConnectorResult(
                    kind="ansible:host_vars",
                    name=host_name,
                    config_json=vars_data,
                    source_id=self.source_id,
                    edges=[{"target_name": host_name, "relation_type": "configures"}],
                )
            )

        return results


def _pull_playbooks(source_path: Path) -> list[dict]:
    """Discover and read playbook files."""
    playbooks: list[dict] = []
    for yml_file in sorted(list(source_path.rglob("*.yml")) + list(source_path.rglob("*.yaml"))):
        if not yml_file.is_file() or yml_file.name in NON_PLAYBOOK_FILES:
            continue
        relative_parts = set(PurePosixPath(yml_file.relative_to(source_path).as_posix()).parts)
        if {"roles", "group_vars", "host_vars"} & relative_parts:
            continue
        try:
            data = yaml.safe_load(yml_file.read_text())
            if isinstance(data, list) and data and _is_playbook(data):
                playbooks.append(
                    {
                        "name": yml_file.stem,
                        "path": str(yml_file.relative_to(source_path)),
                        "plays": data,
                    }
                )
        except yaml.YAMLError as e:
            logger.warning("Failed to parse %s: %s", yml_file, e)
    return playbooks


def _pull_roles(source_path: Path) -> list[dict]:
    """Discover roles from the roles/ directory."""
    roles: list[dict] = []
    for roles_dir in sorted(source_path.rglob("roles")):
        if not roles_dir.is_dir():
            continue
        for role_dir in sorted(roles_dir.iterdir()):
            if role_dir.is_dir():
                role_meta = _load_role_meta(role_dir)
                roles.append(
                    {
                        "name": role_dir.name,
                        "path": str(role_dir.relative_to(source_path)),
                        **role_meta,
                    }
                )
    return roles


def _pull_vars_dir(vars_dir: Path) -> dict[str, Any]:
    """Load all YAML files from a group_vars or host_vars directory."""
    result: dict[str, Any] = {}
    if not vars_dir.is_dir():
        return result
    files = sorted(vars_dir.rglob("*.yml")) + sorted(vars_dir.rglob("*.yaml"))
    for vf in files:
        try:
            data = yaml.safe_load(vf.read_text())
            if data:
                result[vf.stem] = data
        except yaml.YAMLError:
            pass
    return result


def _pull_recursive_vars(source_path: Path, dir_name: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for vars_dir in sorted(source_path.rglob(dir_name)):
        if vars_dir.is_dir():
            result.update(_pull_vars_dir(vars_dir))
    return result


def _is_playbook(data: list) -> bool:
    """Check if a YAML list looks like an Ansible playbook (has hosts/tasks/roles)."""
    if not data:
        return False
    first = data[0]
    if not isinstance(first, dict):
        return False
    playbook_keys = {"hosts", "tasks", "roles", "pre_tasks", "post_tasks", "handlers"}
    return bool(playbook_keys & first.keys())


def _parse_ini_inventory(content: str) -> dict:
    """Parse a simple INI-style Ansible inventory into a YAML-like structure."""
    groups: dict[str, dict] = {}
    current_group = "ungrouped"

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue

        if line.startswith("[") and line.endswith("]"):
            current_group = _parse_ini_section(line[1:-1], groups)
        else:
            _parse_ini_entry(line, current_group, groups)

    return groups


def _parse_ini_section(group_name: str, groups: dict) -> str:
    """Handle an INI section header, return the current group key."""
    if ":children" in group_name:
        base = group_name.replace(":children", "")
        groups.setdefault(base, {"hosts": {}, "children": {}})
        return f"{base}:children"
    if ":vars" in group_name:
        return group_name
    groups.setdefault(group_name, {"hosts": {}, "children": {}})
    return group_name


def _parse_ini_entry(line: str, current_group: str, groups: dict) -> None:
    """Handle a non-section line in an INI inventory."""
    base_group = current_group.split(":")[0]
    groups.setdefault(base_group, {"hosts": {}, "children": {}})

    if current_group.endswith(":children"):
        groups[base_group].setdefault("children", {})[line] = {}
    elif current_group.endswith(":vars"):
        parts = line.split("=", 1)
        if len(parts) == 2:
            groups[base_group].setdefault("vars", {})[parts[0].strip()] = parts[1].strip()
    else:
        parts = line.split()
        host_name = parts[0]
        host_vars = {}
        for part in parts[1:]:
            if "=" in part:
                k, v = part.split("=", 1)
                host_vars[k] = v
        groups[base_group]["hosts"][host_name] = host_vars


def _load_role_meta(role_dir: Path) -> dict:
    """Load role metadata from meta/main.yml and check for key directories."""
    meta: dict[str, Any] = {
        "dependencies": [],
        "has_tasks": (role_dir / "tasks").is_dir(),
        "has_handlers": (role_dir / "handlers").is_dir(),
        "has_templates": (role_dir / "templates").is_dir(),
        "has_defaults": (role_dir / "defaults").is_dir(),
    }

    meta_file = role_dir / "meta" / "main.yml"
    if not meta_file.exists():
        meta_file = role_dir / "meta" / "main.yaml"

    if meta_file.exists():
        try:
            data = yaml.safe_load(meta_file.read_text())
            if isinstance(data, dict):
                meta["dependencies"] = data.get("dependencies", [])
        except yaml.YAMLError:
            pass

    return meta
