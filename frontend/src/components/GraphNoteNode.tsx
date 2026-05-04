import type { Node, NodeProps } from "@xyflow/react";

export type GraphNoteData = {
  content: string;
  noteId: string;
  color?: string;
};

export type GraphNoteNodeType = Node<GraphNoteData, "note">;

export default function GraphNoteNode({ data }: NodeProps<GraphNoteNodeType>) {
  return (
    <div
      className="max-w-[240px] rounded-[18px] border px-3 py-3 text-xs shadow-sm"
      style={{
        background:
          "linear-gradient(180deg, color-mix(in srgb, var(--warning) 10%, var(--bg-card-strong)), color-mix(in srgb, var(--warning) 4%, var(--bg-card)))",
        borderColor: "color-mix(in srgb, var(--warning) 42%, var(--border))",
        color: "var(--text-white)",
        minWidth: 160,
        whiteSpace: "pre-wrap",
        boxShadow: "0 12px 24px rgba(0,0,0,0.18)",
      }}
    >
      <div className="app-kicker mb-2 text-[10px] text-[var(--warning)]">Graph note</div>
      {data.content}
    </div>
  );
}
