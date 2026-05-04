"""Terraform connector: parses tfstate JSON and HCL (.tf) files."""

import json
import logging
import re
from pathlib import Path
from typing import Any

import hcl2

from app.connectors.base import ConnectorResult, IaCConnector
from app.connectors.exceptions import ParseError, PullError
from app.connectors.registry import register

logger = logging.getLogger(__name__)

# Matches Terraform references like ${aws_instance.web.id}, ${var.ami_id},
# ${data.aws_ami.ubuntu.id}, or bare references like aws_vpc.main.id
_REF_PATTERN = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)")


def _normalize_hcl_name(name: str) -> str:
    """Normalize HCL block names returned by python-hcl2."""
    return name.strip().strip('"')


def _extract_refs(value: Any) -> set[str]:
    """Recursively extract Terraform references from config values."""
    refs: set[str] = set()
    if isinstance(value, str):
        for match in _REF_PATTERN.finditer(value):
            refs.add(match.group(1))
    elif isinstance(value, list):
        for item in value:
            refs.update(_extract_refs(item))
    elif isinstance(value, dict):
        for v in value.values():
            refs.update(_extract_refs(v))
    return refs


def _resolve_ref(ref: str) -> tuple[str, str]:
    """Convert a Terraform reference to (target_name, relation_type).

    Examples:
        "var.ami_id"                -> ("var.ami_id", "references")
        "aws_instance.web"          -> ("aws_instance.web", "references")
        "data.aws_ami.ubuntu"       -> ("data.aws_ami.ubuntu", "references")
    """
    # var.xxx -> target is the variable name
    if ref.startswith("var."):
        return ref, "uses_variable"
    # data.type.name -> target is data.type.name
    if ref.startswith("data."):
        return ref, "reads_data"
    # resource_type.name -> target is resource_type.name
    return ref, "references"


@register
class TerraformConnector(IaCConnector):
    connector_type = "terraform"

    async def pull(self) -> dict[str, Any]:
        """Read tfstate and .tf files from the source directory."""
        source_path = Path(self.url)
        if not source_path.is_dir():
            raise PullError(f"Source path is not a directory: {self.url}")

        result: dict[str, Any] = {"tfstate": [], "hcl": []}

        for tfstate_file in sorted(source_path.rglob("*.tfstate")):
            try:
                data = json.loads(tfstate_file.read_text())
                result["tfstate"].append(data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read %s: %s", tfstate_file, e)

        for tf_file in sorted(source_path.rglob("*.tf")):
            try:
                with open(tf_file) as f:
                    data = hcl2.load(f)
                result["hcl"].append(data)
            except Exception as e:
                logger.warning("Failed to parse %s: %s", tf_file, e)

        return result

    async def parse(self, raw_data: dict[str, Any]) -> list[ConnectorResult]:
        """Transform tfstate and HCL data into ConnectorResult objects."""
        try:
            all_nodes = self._collect_tfstate_nodes(raw_data)
            all_nodes.extend(self._collect_hcl_nodes(raw_data))
        except Exception as e:
            raise ParseError(f"Failed to parse Terraform data: {e}") from e

        deduped = _deduplicate(all_nodes)
        _add_implicit_edges(deduped)
        return deduped

    def _collect_tfstate_nodes(self, raw_data: dict) -> list[ConnectorResult]:
        """Extract nodes from all tfstate files."""
        nodes: list[ConnectorResult] = []
        for state in raw_data.get("tfstate", []):
            for resource in state.get("resources", []):
                nodes.extend(self._parse_tfstate_resource(resource))

            for name, output in state.get("outputs", {}).items():
                nodes.append(
                    ConnectorResult(
                        kind="tf:output",
                        name=name,
                        config_json=output,
                        source_id=self.source_id,
                    )
                )
        return nodes

    def _collect_hcl_nodes(self, raw_data: dict) -> list[ConnectorResult]:
        """Extract nodes from all HCL files."""
        nodes: list[ConnectorResult] = []
        for hcl_data in raw_data.get("hcl", []):
            nodes.extend(self._parse_hcl_resources(hcl_data))
            nodes.extend(self._parse_hcl_blocks(hcl_data))
        return nodes

    def _parse_tfstate_resource(self, resource: dict) -> list[ConnectorResult]:
        """Parse a single resource from tfstate."""
        mode = resource.get("mode", "managed")
        res_type = resource.get("type", "unknown")
        name = resource.get("name", "unnamed")

        if mode == "data":
            kind = f"tf:data.{res_type}"
        else:
            kind = f"tf:{res_type}"

        nodes = []
        for instance in resource.get("instances", []):
            attrs = instance.get("attributes", {})
            edges = []

            # Extract depends_on
            for dep in instance.get("dependencies", []):
                edges.append({"target_name": dep, "relation_type": "depends_on"})

            nodes.append(
                ConnectorResult(
                    kind=kind,
                    name=name,
                    config_json=attrs,
                    source_id=self.source_id,
                    edges=edges,
                )
            )

        return nodes

    def _parse_hcl_resources(self, hcl_data: dict) -> list[ConnectorResult]:
        """Parse HCL resource and data blocks."""
        results: list[ConnectorResult] = []

        for resource_block in hcl_data.get("resource", []):
            for res_type, instances in resource_block.items():
                for res_name, config in instances.items():
                    normalized_name = _normalize_hcl_name(res_name)
                    edges = [
                        {
                            "target_name": dep.strip("${}"),
                            "relation_type": "depends_on",
                        }
                        for dep in config.get("depends_on", [])
                        if isinstance(dep, str)
                    ]
                    results.append(
                        ConnectorResult(
                            kind=f"tf:{res_type}",
                            name=normalized_name,
                            config_json=config,
                            source_id=self.source_id,
                            edges=edges,
                        )
                    )

        for data_block in hcl_data.get("data", []):
            for data_type, instances in data_block.items():
                for data_name, config in instances.items():
                    normalized_name = _normalize_hcl_name(data_name)
                    results.append(
                        ConnectorResult(
                            kind=f"tf:data.{data_type}",
                            name=normalized_name,
                            config_json=config,
                            source_id=self.source_id,
                        )
                    )

        return results

    def _parse_hcl_blocks(self, hcl_data: dict) -> list[ConnectorResult]:
        """Parse HCL variable and output blocks."""
        results: list[ConnectorResult] = []

        for var_block in hcl_data.get("variable", []):
            for var_name, config in var_block.items():
                normalized_name = _normalize_hcl_name(var_name)
                results.append(
                    ConnectorResult(
                        kind="tf:variable",
                        name=normalized_name,
                        config_json=config,
                        source_id=self.source_id,
                    )
                )

        for output_block in hcl_data.get("output", []):
            for out_name, config in output_block.items():
                normalized_name = _normalize_hcl_name(out_name)
                results.append(
                    ConnectorResult(
                        kind="tf:output",
                        name=normalized_name,
                        config_json=config,
                        source_id=self.source_id,
                    )
                )

        return results


def _add_implicit_edges(nodes: list[ConnectorResult]) -> None:
    """Scan config values for Terraform references and add edges.

    This connects variables, outputs, and data sources to the resources
    that use them, beyond just explicit depends_on.
    """
    # Build a lookup: "var.ami_id" -> node, "aws_vpc.main" -> node, etc.
    ref_to_name: dict[str, str] = {}
    for node in nodes:
        kind_stripped = node.kind.replace("tf:", "")
        # Resources: "aws_vpc.main"
        ref_to_name[f"{kind_stripped}.{node.name}"] = node.name
        # Variables: "var.name"
        if node.kind == "tf:variable":
            ref_to_name[f"var.{node.name}"] = node.name
        # Data sources: "data.aws_ami.ubuntu"
        if node.kind.startswith("tf:data."):
            data_type = kind_stripped.replace("data.", "")
            ref_to_name[f"data.{data_type}.{node.name}"] = node.name

    # Track existing edges to avoid duplicates
    for node in nodes:
        existing_targets = {e["target_name"] for e in node.edges}
        # Skip depends_on values from config scanning
        config_to_scan = {k: v for k, v in node.config_json.items() if k != "depends_on"}
        refs = _extract_refs(config_to_scan)

        for ref in refs:
            target_name, relation_type = _resolve_ref(ref)
            # Check if this ref points to a known node
            if target_name in ref_to_name:
                resolved = ref_to_name[target_name]
                # Don't add self-references or duplicates
                if resolved != node.name and target_name not in existing_targets:
                    node.edges.append(
                        {
                            "target_name": target_name,
                            "relation_type": relation_type,
                        }
                    )
                    existing_targets.add(target_name)


def _deduplicate(nodes: list[ConnectorResult]) -> list[ConnectorResult]:
    """Remove duplicate nodes, keeping first occurrence but merging edges from all."""
    seen: dict[str, ConnectorResult] = {}
    order: list[str] = []
    for node in nodes:
        key = f"{node.kind}:{node.name}"
        if key not in seen:
            seen[key] = node
            order.append(key)
        else:
            # Merge edges from duplicate into the kept node
            existing = seen[key]
            existing_targets = {(e["target_name"], e["relation_type"]) for e in existing.edges}
            for edge in node.edges:
                edge_key = (edge["target_name"], edge["relation_type"])
                if edge_key not in existing_targets:
                    existing.edges.append(edge)
                    existing_targets.add(edge_key)
    return [seen[k] for k in order]
