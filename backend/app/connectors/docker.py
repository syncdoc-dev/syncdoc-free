"""Docker connector: parses docker-compose.yml and Dockerfile."""

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from app.connectors.base import ConnectorResult, IaCConnector
from app.connectors.exceptions import ParseError, PullError
from app.connectors.registry import register

logger = logging.getLogger(__name__)

COMPOSE_FILENAMES = [
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
]


@register
class DockerConnector(IaCConnector):
    connector_type = "docker"

    async def pull(self) -> dict[str, Any]:
        """Read docker-compose and Dockerfile(s) from the source directory."""
        source_path = Path(self.url)
        if not source_path.is_dir():
            raise PullError(f"Source path is not a directory: {self.url}")

        result: dict[str, Any] = {"compose": [], "dockerfiles": {}}

        for name in COMPOSE_FILENAMES:
            for compose_file in sorted(source_path.rglob(name)):
                try:
                    data = yaml.safe_load(compose_file.read_text())
                    if data:
                        result["compose"].append(data)
                except yaml.YAMLError as e:
                    logger.warning("Failed to parse %s: %s", compose_file, e)

        for dockerfile in sorted(source_path.rglob("Dockerfile*")):
            try:
                relative_name = str(dockerfile.relative_to(source_path))
                result["dockerfiles"][relative_name] = dockerfile.read_text()
            except OSError as e:
                logger.warning("Failed to read %s: %s", dockerfile, e)

        return result

    async def parse(self, raw_data: dict[str, Any]) -> list[ConnectorResult]:
        """Transform Docker data into ConnectorResult objects."""
        results: list[ConnectorResult] = []

        try:
            for compose_data in raw_data.get("compose", []):
                results.extend(self._parse_compose(compose_data))

            for name, content in raw_data.get("dockerfiles", {}).items():
                result = self._parse_dockerfile(name, content)
                if result:
                    results.append(result)

        except Exception as e:
            raise ParseError(f"Failed to parse Docker data: {e}") from e

        return results

    def _parse_compose(self, compose: dict) -> list[ConnectorResult]:
        """Parse a docker-compose.yml into ConnectorResult objects."""
        results: list[ConnectorResult] = []

        # Services
        for svc_name, svc_config in compose.get("services", {}).items():
            edges = []

            # depends_on
            deps = svc_config.get("depends_on", [])
            if isinstance(deps, dict):
                deps = list(deps.keys())
            for dep in deps:
                edges.append({"target_name": dep, "relation_type": "depends_on"})

            # Volume mounts
            for vol in svc_config.get("volumes", []):
                vol_name = vol.split(":")[0] if isinstance(vol, str) else vol.get("source", "")
                if vol_name and not vol_name.startswith((".", "/")):
                    edges.append({"target_name": vol_name, "relation_type": "mounts_volume"})

            # Networks
            svc_networks = svc_config.get("networks", [])
            if isinstance(svc_networks, dict):
                svc_networks = list(svc_networks.keys())
            for net in svc_networks:
                edges.append({"target_name": net, "relation_type": "joins_network"})

            results.append(
                ConnectorResult(
                    kind="docker:service",
                    name=svc_name,
                    config_json=svc_config,
                    source_id=self.source_id,
                    edges=edges,
                )
            )

        # Volumes
        for vol_name, vol_config in compose.get("volumes", {}).items():
            results.append(
                ConnectorResult(
                    kind="docker:volume",
                    name=vol_name,
                    config_json=vol_config or {},
                    source_id=self.source_id,
                )
            )

        # Networks
        for net_name, net_config in compose.get("networks", {}).items():
            results.append(
                ConnectorResult(
                    kind="docker:network",
                    name=net_name,
                    config_json=net_config or {},
                    source_id=self.source_id,
                )
            )

        return results

    def _parse_dockerfile(self, filename: str, content: str) -> ConnectorResult | None:
        """Parse a Dockerfile into a ConnectorResult."""
        config: dict[str, Any] = {
            "filename": filename,
            "stages": [],
            "ports": [],
            "volumes": [],
            "healthcheck": None,
        }
        edges: list[dict[str, str]] = []

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # FROM
            from_match = re.match(r"^FROM\s+(\S+)(?:\s+AS\s+(\S+))?", line, re.IGNORECASE)
            if from_match:
                base_image = from_match.group(1)
                stage_name = from_match.group(2)
                config["stages"].append({"base": base_image, "name": stage_name})

            # EXPOSE
            expose_match = re.match(r"^EXPOSE\s+(.+)", line, re.IGNORECASE)
            if expose_match:
                config["ports"].extend(expose_match.group(1).split())

            # VOLUME
            vol_match = re.match(r"^VOLUME\s+(.+)", line, re.IGNORECASE)
            if vol_match:
                config["volumes"].append(vol_match.group(1))

            # HEALTHCHECK
            hc_match = re.match(r"^HEALTHCHECK\s+(.+)", line, re.IGNORECASE)
            if hc_match:
                config["healthcheck"] = hc_match.group(1)

            # COPY --from=stage (multi-stage build edge)
            copy_from = re.match(r"^COPY\s+--from=(\S+)", line, re.IGNORECASE)
            if copy_from:
                edges.append({"target_name": copy_from.group(1), "relation_type": "copies_from"})

        if not config["stages"]:
            return None

        # Use the final stage's base image as the name
        image_name = config["stages"][-1]["base"]

        return ConnectorResult(
            kind="docker:image",
            name=image_name,
            config_json=config,
            source_id=self.source_id,
            edges=edges,
        )
