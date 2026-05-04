import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  Server,
  Shield,
  Variable,
  ArrowRightFromLine,
  Database,
  HardDrive,
  Key,
  Dice5,
  Monitor,
  Users,
  ScrollText,
  FolderCog,
  Container,
  Network,
  Box,
} from "lucide-react";

export type InfraNodeData = {
  label: string;
  kind: string;
  resourceType: string;
  direction: "LR" | "TB";
};

function getIcon(kind: string): React.ElementType {
  if (kind === "tf:variable") return Variable;
  if (kind === "tf:output") return ArrowRightFromLine;
  if (kind.startsWith("tf:data.")) return Database;
  if (kind.includes("s3") || kind.includes("dynamodb")) return HardDrive;
  if (kind.includes("security_group") || kind.includes("iam")) return Shield;
  if (kind.includes("kms")) return Key;
  if (kind.includes("random")) return Dice5;
  if (kind.startsWith("tf:")) return Server;
  if (kind === "docker:service") return Container;
  if (kind === "docker:volume") return HardDrive;
  if (kind === "docker:network") return Network;
  if (kind === "docker:image") return Box;
  if (kind.startsWith("docker:")) return Container;
  if (kind === "ansible:host" || kind === "ansible:host_vars") return Monitor;
  if (kind === "ansible:group" || kind === "ansible:group_vars") return Users;
  if (kind === "ansible:playbook") return ScrollText;
  if (kind === "ansible:role") return FolderCog;
  if (kind.startsWith("ansible:")) return ScrollText;
  return Server;
}

export function getToolFromKind(kind: string): string {
  const colon = kind.indexOf(":");
  return colon > 0 ? kind.slice(0, colon) : "other";
}

export const TOOL_COLORS: Record<string, { hex: string; glow: string; label: string }> = {
  tf: { hex: "#b596ff", glow: "rgba(181, 150, 255, 0.25)", label: "Terraform" },
  docker: { hex: "#5aa4ff", glow: "rgba(90, 164, 255, 0.25)", label: "Docker" },
  ansible: { hex: "#ff7a6b", glow: "rgba(255, 122, 107, 0.22)", label: "Ansible" },
  git: { hex: "#ffb347", glow: "rgba(255, 179, 71, 0.22)", label: "Git" },
  other: { hex: "#7a879f", glow: "rgba(122, 135, 159, 0.18)", label: "Other" },
};

function kindLabel(kind: string): string {
  return kind
    .replace(/^tf:/, "")
    .replace(/^ansible:/, "")
    .replace(/^docker:/, "")
    .replace(/_/g, " ");
}

function InfraNodeComponent({ data }: NodeProps) {
  const nodeData = data as unknown as InfraNodeData;
  const Icon = getIcon(nodeData.kind);
  const isVertical = nodeData.direction === "TB";
  const tool = getToolFromKind(nodeData.kind);
  const tone = TOOL_COLORS[tool] ?? TOOL_COLORS.other;

  return (
    <>
      <Handle
        type="target"
        position={isVertical ? Position.Top : Position.Left}
        className="!h-3 !w-3 !border-2"
        style={{
          background: "var(--bg-card-strong)",
          borderColor: tone.hex,
          boxShadow: `0 0 0 3px ${tone.glow}`,
        }}
      />
      <div
        className="min-w-[190px] max-w-[240px] rounded-[22px] border px-4 py-3 transition-transform duration-200 hover:-translate-y-0.5"
        style={{
          background:
            `linear-gradient(180deg, color-mix(in srgb, ${tone.hex} 10%, var(--bg-card-strong)), var(--bg-card))`,
          borderColor: "color-mix(in srgb, var(--border-bright) 55%, var(--border))",
          boxShadow: `var(--graph-node-shadow), inset 0 1px 0 rgba(255,255,255,0.03), 0 0 0 1px ${tone.glow}`,
        }}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <span
            className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border"
            style={{
              borderColor: `color-mix(in srgb, ${tone.hex} 42%, var(--border))`,
              background: tone.glow,
              color: tone.hex,
            }}
          >
            <Icon className="h-4.5 w-4.5" />
          </span>
          <span
            className="app-kicker rounded-full border px-2.5 py-1 text-[10px]"
            style={{
              borderColor: `color-mix(in srgb, ${tone.hex} 42%, var(--border))`,
              background: "color-mix(in srgb, var(--bg-input) 88%, transparent)",
              color: tone.hex,
            }}
          >
            {TOOL_COLORS[tool]?.label ?? "Resource"}
          </span>
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[var(--text-white)]">{nodeData.label}</p>
          <p className="mt-1 truncate text-[11px] uppercase tracking-[0.12em] text-[var(--text-muted)]">
            {kindLabel(nodeData.kind)}
          </p>
        </div>
      </div>
      <Handle
        type="source"
        position={isVertical ? Position.Bottom : Position.Right}
        className="!h-3 !w-3 !border-2"
        style={{
          background: "var(--bg-card-strong)",
          borderColor: tone.hex,
          boxShadow: `0 0 0 3px ${tone.glow}`,
        }}
      />
    </>
  );
}

export default memo(InfraNodeComponent);
