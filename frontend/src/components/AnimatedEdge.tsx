import { BaseEdge, getBezierPath, type EdgeProps } from "@xyflow/react";

export default function AnimatedEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style,
}: EdgeProps) {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const label = (data as Record<string, unknown>)?.label as string | undefined;
  const opacity = typeof style?.opacity === "number" ? style.opacity : 1;

  return (
    <>
      <svg className="absolute overflow-visible pointer-events-none">
        <defs>
          <linearGradient id={`edge-gradient-${id}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--graph-edge)" stopOpacity={opacity} />
            <stop offset="55%" stopColor="var(--graph-edge-active)" stopOpacity={opacity} />
            <stop offset="100%" stopColor="var(--accent-icon)" stopOpacity={opacity} />
          </linearGradient>
        </defs>
      </svg>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: `url(#edge-gradient-${id})`,
          strokeWidth: 1.8,
          opacity,
        }}
      />
      <circle r="3.4" fill="var(--accent)" opacity={opacity}>
        <animateMotion dur="3.6s" repeatCount="indefinite" path={edgePath} />
      </circle>
      {label && (
        <text>
          <textPath
            href={`#${id}`}
            startOffset="50%"
            textAnchor="middle"
            className="fill-[var(--text-muted)] text-[9px] uppercase tracking-[0.18em]"
            dy="-8"
          >
            {label}
          </textPath>
        </text>
      )}
    </>
  );
}
