import { memo } from "react";
import { type NodeProps } from "@xyflow/react";

export interface SourceGroupData {
  label: string;
  toolColor: string;
}

function SourceGroupNode({ data }: NodeProps) {
  const { label, toolColor } = data as unknown as SourceGroupData;
  return (
    <div className="h-full w-full overflow-hidden rounded-[24px]">
      <div className="brand-ribbon h-[2px] w-full opacity-60" />
      <div className="px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <span
            className="app-kicker rounded-full border px-2.5 py-1 text-[10px]"
            style={{
              color: toolColor,
              borderColor: `color-mix(in srgb, ${toolColor} 42%, var(--border))`,
              background: "color-mix(in srgb, var(--bg-input) 88%, transparent)",
            }}
          >
            source
          </span>
          <span className="h-2 w-2 rounded-full" style={{ background: toolColor }} />
        </div>
        <div className="mt-3 text-sm font-semibold text-[var(--text-white)]">{label}</div>
      </div>
    </div>
  );
}

export default memo(SourceGroupNode);
