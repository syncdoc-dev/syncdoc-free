import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from "@xyflow/react";

export default function ManualEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, data, id, style } = props;
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });
  const color = (data?.color as string) || "var(--warning)";
  const label = (data?.label as string) || "";
  const opacity = typeof style?.opacity === "number" ? style.opacity : 1;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{ stroke: color, strokeWidth: 2.2, strokeDasharray: "7 5", opacity }}
      />
      {label ? (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              background: "color-mix(in srgb, var(--bg-card-strong) 90%, transparent)",
              padding: "4px 8px",
              borderRadius: 999,
              border: `1px solid ${color}66`,
              fontSize: 10,
              color: "var(--text-secondary)",
              opacity,
            }}
            className="nodrag nopan uppercase tracking-[0.16em]"
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
}
