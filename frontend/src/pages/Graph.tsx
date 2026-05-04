import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  BackgroundVariant,
  Panel,
  type EdgeChange,
  type NodeChange,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import dagre from "dagre";
import "@xyflow/react/dist/style.css";
import { Network } from "lucide-react";
import {
  createGraphNote,
  createManualEdge,
  deleteGraphNote,
  deleteManualEdge,
  getGraph,
  getSources,
  updateGraphNote,
  updateManualEdge,
} from "../api/client";
import type { GraphData, Source } from "../types";
import InfraNodeComponent, {
  type InfraNodeData,
  getToolFromKind,
  TOOL_COLORS,
} from "../components/InfraNode";
import AnimatedEdge from "../components/AnimatedEdge";
import SourceGroupNode from "../components/SourceGroupNode";
import GraphNoteNode, { type GraphNoteNodeType } from "../components/GraphNoteNode";
import ManualEdge from "../components/ManualEdge";
import { useAuth } from "../context/AuthContext";
import UpgradeBadge from "../components/UpgradeBadge";

const nodeTypes = { infra: InfraNodeComponent, sourceGroup: SourceGroupNode, note: GraphNoteNode };
const edgeTypes = { animated: AnimatedEdge, manual: ManualEdge };

const NODE_WIDTH = 210;
const NODE_HEIGHT = 110;
const CLUSTER_GAP = 160;
const GROUP_PADDING = 40;
const GROUP_HEADER = 40;

// ── Layout helpers ──────────────────────────────────────────────────

/** Layout a single cluster of nodes with dagre and return positioned nodes. */
function layoutCluster(
  clusterNodes: GraphData["nodes"],
  clusterEdges: GraphData["edges"],
  direction: "LR" | "TB",
): { nodes: Node[]; edges: Edge[]; width: number; height: number } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: direction,
    nodesep: 30,
    ranksep: 80,
    edgesep: 20,
    marginx: 20,
    marginy: 20,
  });

  const nodeIds = new Set(clusterNodes.map((n) => n.id));

  for (const node of clusterNodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }

  // Only include edges where both endpoints are in this cluster
  const internalEdges = clusterEdges.filter(
    (e) => nodeIds.has(e.from_node_id) && nodeIds.has(e.to_node_id),
  );
  for (const edge of internalEdges) {
    g.setEdge(edge.from_node_id, edge.to_node_id);
  }

  dagre.layout(g);

  let maxX = 0;
  let maxY = 0;

  const nodes: Node[] = clusterNodes.map((n) => {
    const pos = g.node(n.id);
    const x = pos.x - NODE_WIDTH / 2;
    const y = pos.y - NODE_HEIGHT / 2;
    if (pos.x + NODE_WIDTH / 2 > maxX) maxX = pos.x + NODE_WIDTH / 2;
    if (pos.y + NODE_HEIGHT / 2 > maxY) maxY = pos.y + NODE_HEIGHT / 2;
    return {
      id: n.id,
      type: "infra",
      position: { x, y },
      data: {
        label: n.name,
        kind: n.kind,
        resourceType: n.kind,
        direction,
      } satisfies InfraNodeData,
    };
  });

  const edges: Edge[] = internalEdges.map((e) => ({
    id: e.id,
    source: e.from_node_id,
    target: e.to_node_id,
    type: "animated",
    data: { label: e.relation_type.replace(/_/g, " ") },
  }));

  return { nodes, edges, width: maxX, height: maxY };
}

/** Layout graph with each source in its own visual group box. */
function layoutGraph(
  graphData: GraphData,
  direction: "LR" | "TB" = "TB",
  sources: Source[],
): { nodes: Node[]; edges: Edge[] } {
  // Group nodes by source_id
  const sourceGroups = new Map<string, GraphData["nodes"]>();
  for (const node of graphData.nodes) {
    const sid = node.source_id || "_unknown";
    if (!sourceGroups.has(sid)) sourceGroups.set(sid, []);
    sourceGroups.get(sid)!.push(node);
  }

  const sourceMap = new Map(sources.map((s) => [s.id, s]));
  const allNodes: Node[] = [];
  const allEdges: Edge[] = [];
  let offsetX = 0;

  // Sort by source URL for consistent ordering
  const sortedSourceIds = [...sourceGroups.keys()].sort((a, b) => {
    const sa = sourceMap.get(a);
    const sb = sourceMap.get(b);
    return (sa?.url ?? a).localeCompare(sb?.url ?? b);
  });

  for (const sourceId of sortedSourceIds) {
    const clusterNodeData = sourceGroups.get(sourceId)!;
    const { nodes, edges, width, height } = layoutCluster(
      clusterNodeData,
      graphData.edges,
      direction,
    );

    // Determine group label and color
    const source = sourceMap.get(sourceId);
    const sourceName = source
      ? `${source.url.split("/").pop()} (${source.type})`
      : sourceId;
    const toolKey = source
      ? ({ terraform: "tf", docker: "docker", ansible: "ansible", git: "git", ci_cd: "other" } as Record<string, string>)[source.type] ?? "other"
      : "other";
    const toolColor = TOOL_COLORS[toolKey]?.hex ?? TOOL_COLORS.other.hex;

    // Create a group (parent) node as the box
    const groupId = `group-${sourceId}`;
    const groupWidth = width + GROUP_PADDING * 2;
    const groupHeight = height + GROUP_PADDING * 2 + GROUP_HEADER;

    allNodes.push({
      id: groupId,
      type: "sourceGroup",
      position: { x: offsetX, y: 0 },
      data: { label: sourceName, toolColor },
      style: {
        width: groupWidth,
        height: groupHeight,
        background:
          `linear-gradient(180deg, color-mix(in srgb, ${toolColor} 8%, var(--bg-card-strong)), color-mix(in srgb, ${toolColor} 3%, var(--bg-card)))`,
        border: `1.5px solid color-mix(in srgb, ${toolColor} 35%, var(--border))`,
        borderRadius: 24,
        padding: 0,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.03)",
      },
    });

    // Offset child nodes inside the group box
    for (const node of nodes) {
      node.position.x += GROUP_PADDING;
      node.position.y += GROUP_PADDING + GROUP_HEADER;
      node.parentId = groupId;
      node.extent = "parent";
      allNodes.push(node);
    }
    allEdges.push(...edges);

    offsetX += groupWidth + CLUSTER_GAP;
  }

  // Do NOT auto-add cross-source edges — those require explicit user action
  return { nodes: allNodes, edges: allEdges };
}

// ── Minimap color ───────────────────────────────────────────────────

function getMinimapColor(node: Node): string {
  const kind = (node.data as InfraNodeData)?.kind || "";
  const tool = getToolFromKind(kind);
  return TOOL_COLORS[tool]?.hex ?? TOOL_COLORS.other.hex;
}

// ── Component ───────────────────────────────────────────────────────

function GraphInner() {
  const { user, entitlements, hasFeature } = useAuth();
  const canEdit = user?.role && ["member", "admin", "owner"].includes(user.role);
  const entitlementsLoaded = entitlements !== null;
  const canUseGraphNotes = !entitlementsLoaded || hasFeature("graph_annotations");
  const canUseManualEdges = !entitlementsLoaded || hasFeature("manual_graph_edges");
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>("");
  const [direction, setDirection] = useState<"LR" | "TB">("LR");
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [selectedInfraId, setSelectedInfraId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isolate, setIsolate] = useState(false);
  const [highlightMode, setHighlightMode] = useState<"both" | "upstream" | "downstream">(
    "both",
  );
  const [manualEdgeColor, setManualEdgeColor] = useState("#ffb347");

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition, setCenter } = useReactFlow();

  useEffect(() => {
    getSources().then(setSources).catch(() => {});
  }, []);

  useEffect(() => {
    getGraph(selectedSource || undefined)
      .then(setGraphData)
      .catch(() => setGraphData({ nodes: [], edges: [] }));
  }, [selectedSource]);

  useEffect(() => {
    if (!graphData || graphData.nodes.length === 0) return;
    const { nodes: n, edges: e } = layoutGraph(graphData, direction, sources);
    const notes = graphData.notes ?? [];
    const manualEdges = graphData.manual_edges ?? [];

    const noteNodes: GraphNoteNodeType[] = notes.map((note) => ({
      id: `note-${note.id}`,
      type: "note",
      position: { x: note.pos_x, y: note.pos_y },
      data: { content: note.content, noteId: note.id },
      draggable: true,
    }));

    const manualFlowEdges: Edge[] = manualEdges.map((edge) => ({
      id: `manual-${edge.id}`,
      source: edge.from_node_id,
      target: edge.to_node_id,
      type: "manual",
      data: { manualId: edge.id, label: edge.label, color: edge.color },
    }));

    setNodes([...n, ...noteNodes]);
    setEdges([...e, ...manualFlowEdges]);
  }, [graphData, direction, sources, setNodes, setEdges]);

  // Build legend dynamically from the tools present in the data
  const legend = useMemo(() => {
    if (!graphData) return [];
    const tools = new Set(graphData.nodes.map((n) => getToolFromKind(n.kind)));
    return [...tools]
      .sort()
      .map((t) => TOOL_COLORS[t] ?? TOOL_COLORS.other)
      .map(({ label, hex }) => ({ label, color: hex }));
  }, [graphData]);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);
      if (!canEdit) return;
      for (const change of changes) {
        if (change.type === "remove") {
          const noteId = change.id.startsWith("note-") ? change.id.replace("note-", "") : null;
          if (noteId) {
            deleteGraphNote(noteId).catch(() => {});
          }
        }
      }
    },
    [onNodesChange, canEdit],
  );

  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      onEdgesChange(changes);
      if (!canEdit) return;
      for (const change of changes) {
        if (change.type === "remove") {
          const manualId = change.id.startsWith("manual-") ? change.id.replace("manual-", "") : null;
          if (manualId) {
            deleteManualEdge(manualId).catch(() => {});
          }
        }
      }
    },
    [onEdgesChange, canEdit],
  );

  const selectedEdge = edges.find((e) => e.id === selectedEdgeId);
  const selectedNote = nodes.find((n) => n.id === selectedNoteId);
  const selectedInfra = nodes.find((n) => n.id === selectedInfraId);

  const searchableNodes = useMemo(
    () => nodes.filter((n) => n.type === "infra"),
    [nodes],
  );
  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return [];
    return searchableNodes.filter((n) =>
      String((n.data as InfraNodeData)?.label || "").toLowerCase().includes(q),
    );
  }, [searchQuery, searchableNodes]);

  const { highlightedNodes, highlightedEdges } = useMemo(() => {
    if (!selectedInfraId) {
      return { highlightedNodes: new Set<string>(), highlightedEdges: new Set<string>() };
    }
    const outgoing = new Map<string, string[]>();
    const incoming = new Map<string, string[]>();
    edges.forEach((edge) => {
      if (!edge.source || !edge.target) return;
      if (!outgoing.has(edge.source)) outgoing.set(edge.source, []);
      if (!incoming.has(edge.target)) incoming.set(edge.target, []);
      outgoing.get(edge.source)!.push(edge.target);
      incoming.get(edge.target)!.push(edge.source);
    });

    const collect = (start: string, dir: "out" | "in") => {
      const visited = new Set<string>();
      const queue = [start];
      while (queue.length) {
        const current = queue.shift()!;
        const nextList = dir === "out" ? outgoing.get(current) || [] : incoming.get(current) || [];
        for (const next of nextList) {
          if (!visited.has(next)) {
            visited.add(next);
            queue.push(next);
          }
        }
      }
      return visited;
    };

    const upstream = collect(selectedInfraId, "in");
    const downstream = collect(selectedInfraId, "out");
    const nodesSet = new Set<string>([selectedInfraId]);
    if (highlightMode === "both" || highlightMode === "upstream") {
      upstream.forEach((n) => nodesSet.add(n));
    }
    if (highlightMode === "both" || highlightMode === "downstream") {
      downstream.forEach((n) => nodesSet.add(n));
    }

    const edgesSet = new Set<string>();
    edges.forEach((edge) => {
      if (!edge.source || !edge.target) return;
      if (nodesSet.has(edge.source) && nodesSet.has(edge.target)) {
        edgesSet.add(edge.id);
      }
    });
    return { highlightedNodes: nodesSet, highlightedEdges: edgesSet };
  }, [edges, selectedInfraId, highlightMode]);

  const displayNodes = useMemo(() => {
    if (!selectedInfraId) return nodes;
    return nodes.map((node) => {
      const isHighlighted = highlightedNodes.has(node.id);
      const isGroup = node.type === "sourceGroup";
      const opacity = isolate ? (isHighlighted || isGroup ? 1 : 0.15) : isHighlighted ? 1 : 0.35;
      return {
        ...node,
        style: {
          ...(node.style || {}),
          opacity,
        },
      };
    });
  }, [nodes, highlightedNodes, selectedInfraId, isolate]);

  const displayEdges = useMemo(() => {
    if (!selectedInfraId) return edges;
    return edges.map((edge) => {
      const isHighlighted = highlightedEdges.has(edge.id);
      return {
        ...edge,
        style: {
          ...(edge.style || {}),
          opacity: isolate ? (isHighlighted ? 1 : 0.15) : isHighlighted ? 1 : 0.35,
        },
      };
    });
  }, [edges, highlightedEdges, selectedInfraId, isolate]);

  const addNote = async () => {
    if (!canEdit || !canUseGraphNotes || !wrapperRef.current) return;
    const bounds = wrapperRef.current.getBoundingClientRect();
    const position = screenToFlowPosition({
      x: bounds.left + bounds.width / 2,
      y: bounds.top + bounds.height / 2,
    });
    const content = window.prompt("Note text:", "New note");
    if (!content) return;
    try {
        const created = await createGraphNote({
          content,
          pos_x: position.x,
          pos_y: position.y,
          source_id: selectedSource || null,
        });
      setNodes((prev) => [
        ...prev,
        {
          id: `note-${created.id}`,
          type: "note",
          position: { x: created.pos_x, y: created.pos_y },
          data: { content: created.content, noteId: created.id },
          draggable: true,
        },
      ]);
    } catch {
      // ignore
    }
  };

  const isEmptyGraph = Boolean(graphData && graphData.nodes.length === 0);

  return (
    <div className="grid min-h-[calc(100vh-14rem)] grid-rows-[auto_minmax(0,1fr)_auto] gap-4">
      <div className="app-panel rounded-[30px] p-5 sm:p-6">
        <div className="mb-4 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="app-kicker text-sm text-[var(--accent)]">Topology explorer</div>
            <h2 className="app-section-title mt-2 text-4xl text-[var(--text-white)]">
              Service dependency graph
            </h2>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              {graphData
                ? `${graphData.nodes.length} resources · ${graphData.edges.length} dependencies`
                : "Loading graph data..."}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {sources.length > 1 && (
              <select
                value={selectedSource}
                onChange={(e) => setSelectedSource(e.target.value)}
                className="rounded-full border border-[var(--border)] bg-[var(--bg-input)]/90 px-4 py-2 text-sm text-[var(--text-primary)]"
              >
                <option value="">All sources</option>
                {sources.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.url.split("/").pop()} ({s.type})
                  </option>
                ))}
              </select>
            )}
            <div className="flex overflow-hidden rounded-full border border-[var(--border)] bg-[var(--bg-input)]/70 p-1">
              {(["LR", "TB"] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDirection(d)}
                  className={`rounded-full px-4 py-2 text-xs font-medium transition-colors ${
                    direction === d
                      ? "bg-[var(--accent-bg)] text-[var(--text-white)]"
                      : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                  }`}
                >
                  {d === "LR" ? "Horizontal" : "Vertical"}
                </button>
              ))}
            </div>
            {canEdit && (
              <div className="flex items-center gap-2">
                {!canUseGraphNotes && <UpgradeBadge label="Pro" />}
                <button
                  onClick={addNote}
                  disabled={!canUseGraphNotes}
                  className="rounded-full border border-[var(--border)] bg-[var(--bg-input)]/90 px-4 py-2 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Add note
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="app-panel relative min-h-[420px] overflow-hidden rounded-[32px] p-3 sm:p-4" ref={wrapperRef}>
        {!graphData ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-7 w-7 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
          </div>
        ) : isEmptyGraph ? (
          <div className="flex h-full flex-col items-center justify-center rounded-[26px] border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-muted)]">
            <Network className="mb-3 h-10 w-10" />
            <p className="text-base font-medium text-[var(--text-white)]">No infrastructure nodes yet</p>
            <p className="mt-1 text-sm">
              Add a source and sync to see the dependency graph
            </p>
          </div>
        ) : (
          <div
            className="h-full w-full overflow-auto rounded-[26px] border border-[var(--border)]"
            style={{ background: "color-mix(in srgb, var(--bg-secondary) 76%, transparent)" }}
          >
            <ReactFlow
              nodes={displayNodes}
              edges={displayEdges}
              onNodesChange={handleNodesChange}
              onEdgesChange={handleEdgesChange}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              // Remove fitView to allow proper scrolling
              minZoom={0.2}
              maxZoom={2}
              proOptions={{ hideAttribution: true }}
              className="bg-transparent"
              style={{
                width: "100%",
                height: "100%",
                transform: "none",
              }}
              onEdgeClick={(_, edge) => {
                if (edge.id.startsWith("manual-")) {
                  setSelectedEdgeId(edge.id);
                  setSelectedNoteId(null);
                  setSelectedInfraId(null);
                }
              }}
              onNodeClick={(_, node) => {
                if (node.id.startsWith("note-")) {
                  setSelectedNoteId(node.id);
                  setSelectedEdgeId(null);
                  setSelectedInfraId(null);
                  return;
                }
                if (node.type === "infra") {
                  setSelectedInfraId(node.id);
                  setSelectedEdgeId(null);
                  setSelectedNoteId(null);
                }
              }}
              onNodeDragStop={(_, node) => {
                if (!canEdit || !node.id.startsWith("note-")) return;
                const noteId = node.data?.noteId as string | undefined;
                if (!noteId) return;
                updateGraphNote(noteId, { pos_x: node.position.x, pos_y: node.position.y }).catch(
                  () => {},
                );
              }}
              onConnect={async (params) => {
                if (!canEdit || !canUseManualEdges || !params.source || !params.target) return;
                try {
                  const created = await createManualEdge({
                    from_node_id: params.source,
                    to_node_id: params.target,
                    color: manualEdgeColor,
                  });
                  setEdges((prev) => [
                    ...prev,
                    {
                      id: `manual-${created.id}`,
                      source: created.from_node_id,
                      target: created.to_node_id,
                      type: "manual",
                      data: { manualId: created.id, label: created.label, color: created.color },
                    },
                  ]);
                } catch {
                  // ignore
                }
              }}
              nodesConnectable={!!canEdit && canUseManualEdges}
            >
              <Background
                variant={BackgroundVariant.Dots}
                gap={24}
                size={1.2}
                color="var(--graph-grid)"
              />
              <Controls
                className="!shadow-xl"
              />
              <MiniMap
                nodeColor={getMinimapColor}
                maskColor="rgba(0, 0, 0, 0.6)"
                className="!border-[var(--border)]"
                pannable
                zoomable
              />
              <Panel position="bottom-left">
                <div className="rounded-[22px] border border-[var(--border)] bg-[var(--bg-card-strong)]/90 p-3 backdrop-blur">
                  <div className="app-kicker mb-2 text-[10px] text-[var(--text-muted)]">Legend</div>
                  <div className="flex flex-wrap gap-2">
                  {legend.map(({ label, color }) => (
                    <span
                      key={label}
                      className="flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--bg-input)]/70 px-2.5 py-1 text-[10px] text-[var(--text-secondary)]"
                    >
                      <span className="h-2 w-2 rounded-full" style={{ background: color }} />
                      {label}
                    </span>
                  ))}
                  </div>
                </div>
              </Panel>
              {canEdit && canUseManualEdges && selectedEdge && selectedEdge.id.startsWith("manual-") && (
                <Panel position="bottom-right">
                  <div className="flex min-w-[240px] flex-col gap-3 rounded-[22px] border border-[var(--border)] bg-[var(--bg-card-strong)]/90 p-3 backdrop-blur">
                    <div className="app-kicker text-[10px] text-[var(--text-secondary)]">
                      Manual Edge
                    </div>
                    <input
                      type="text"
                      value={(selectedEdge.data?.label as string) || ""}
                      onChange={(e) => {
                        const value = e.target.value;
                        setEdges((prev) =>
                          prev.map((edge) =>
                            edge.id === selectedEdge.id
                              ? { ...edge, data: { ...edge.data, label: value } }
                              : edge,
                          ),
                        );
                      }}
                      placeholder="Label"
                      className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-input)] px-3 py-2 text-xs text-[var(--text-primary)]"
                    />
                    <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                      <span>Color</span>
                      <input
                        type="color"
                        value={(selectedEdge.data?.color as string) || manualEdgeColor}
                        onChange={(e) => {
                          const value = e.target.value;
                          setEdges((prev) =>
                            prev.map((edge) =>
                              edge.id === selectedEdge.id
                                ? { ...edge, data: { ...edge.data, color: value } }
                                : edge,
                            ),
                          );
                        }}
                        className="h-8 w-10 rounded-xl border border-[var(--border)] bg-transparent"
                      />
                    </div>
                    <button
                      className="rounded-full border border-[var(--border-light)] px-3 py-2 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)]"
                      onClick={async () => {
                        const manualId = selectedEdge.data?.manualId as string | undefined;
                        if (!manualId) return;
                        await updateManualEdge(manualId, {
                          label: (selectedEdge.data?.label as string) || null,
                          color: (selectedEdge.data?.color as string) || manualEdgeColor,
                        }).catch(() => {});
                      }}
                    >
                      Save
                    </button>
                  </div>
                </Panel>
              )}
              {canEdit && selectedNote && selectedNote.id.startsWith("note-") && (
                <Panel position="bottom-right">
                  <div className="flex min-w-[240px] flex-col gap-3 rounded-[22px] border border-[var(--border)] bg-[var(--bg-card-strong)]/90 p-3 backdrop-blur">
                    <div className="app-kicker text-[10px] text-[var(--text-secondary)]">
                      Note
                    </div>
                    <button
                      className="rounded-full border border-[var(--border-light)] px-3 py-2 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)]"
                      onClick={async () => {
                        const noteId = selectedNote.data?.noteId as string | undefined;
                        if (!noteId) return;
                        const content = window.prompt("Update note:", selectedNote.data?.content as string);
                        if (!content) return;
                        await updateGraphNote(noteId, { content }).catch(() => {});
                        setNodes((prev) =>
                          prev.map((node) =>
                            node.id === selectedNote.id
                              ? { ...node, data: { ...node.data, content } }
                              : node,
                          ),
                        );
                      }}
                    >
                      Edit Note
                    </button>
                    <button
                      className="rounded-full border px-3 py-2 text-xs font-medium transition-colors"
                      style={{
                        borderColor: "color-mix(in srgb, var(--danger) 45%, var(--border))",
                        color: "var(--danger)",
                      }}
                      onClick={async () => {
                        const noteId = selectedNote.data?.noteId as string | undefined;
                        if (!noteId) return;
                        await deleteGraphNote(noteId).catch(() => {});
                        setNodes((prev) => prev.filter((node) => node.id !== selectedNote.id));
                        setSelectedNoteId(null);
                      }}
                    >
                      Delete Note
                    </button>
                  </div>
                </Panel>
              )}
            </ReactFlow>
          </div>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2 lg:items-start">
        <div className="app-panel flex h-full flex-col gap-3 rounded-[26px] p-4">
          <div className="app-kicker text-[10px] text-[var(--text-secondary)]">
            Focus
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search nodes"
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg-input)] px-3 py-2 text-xs text-[var(--text-primary)]"
          />
          {searchResults.length > 0 && (
            <div className="max-h-40 overflow-auto rounded-2xl border border-[var(--border)] bg-[var(--bg-input)]">
              {searchResults.slice(0, 8).map((n) => (
                <button
                  key={n.id}
                  onClick={() => {
                    setSelectedInfraId(n.id);
                    setSelectedEdgeId(null);
                    setSelectedNoteId(null);
                    const pos = n.position || { x: 0, y: 0 };
                    setCenter(pos.x + NODE_WIDTH / 2, pos.y + NODE_HEIGHT / 2, {
                      zoom: 1.2,
                      duration: 300,
                    });
                  }}
                  className="w-full px-3 py-2 text-left text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)]"
                >
                  {(n.data as InfraNodeData)?.label || n.id}
                </button>
              ))}
            </div>
          )}
          <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
            <span>Highlight</span>
            <select
              value={highlightMode}
              onChange={(e) => setHighlightMode(e.target.value as typeof highlightMode)}
              className="rounded-xl border border-[var(--border)] bg-[var(--bg-input)] px-2 py-1 text-xs text-[var(--text-primary)]"
            >
              <option value="both">Both</option>
              <option value="upstream">Upstream</option>
              <option value="downstream">Downstream</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
            <input
              type="checkbox"
              checked={isolate}
              onChange={(e) => setIsolate(e.target.checked)}
            />
            Isolate selection
          </label>
          {selectedInfra && (
            <div className="text-[10px] text-[var(--text-secondary)]">
              Selected: {(selectedInfra.data as InfraNodeData)?.label || selectedInfra.id}
            </div>
          )}
        </div>

        {canEdit ? (
          <div className="app-panel flex h-full flex-col gap-3 rounded-[26px] p-4">
            <div className="flex items-center gap-2">
              <div className="app-kicker text-[10px] text-[var(--text-secondary)]">
                Manual Connectors
              </div>
              {!canUseManualEdges && <UpgradeBadge label="Pro" />}
            </div>
            <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
              <span>Color</span>
              <input
                type="color"
                value={manualEdgeColor}
                onChange={(e) => setManualEdgeColor(e.target.value)}
                disabled={!canUseManualEdges}
                className="h-8 w-10 rounded-xl border border-[var(--border)] bg-transparent"
              />
            </div>
            <div className="flex items-center gap-2">
              <div className="app-kicker text-[10px] text-[var(--text-secondary)]">
                Notes
              </div>
              {!canUseGraphNotes && <UpgradeBadge label="Pro" />}
            </div>
            <div className="text-xs text-[var(--text-secondary)]">
              {canUseManualEdges
                ? "Drag between nodes to add manual connections."
                : "Upgrade your license to add manual connections."}
            </div>
            <div className="text-xs text-[var(--text-secondary)]">
              {canUseGraphNotes
                ? "Notes use a fixed style."
                : "Upgrade your license to add graph notes."}
            </div>
          </div>
        ) : (
          <div className="hidden lg:block" />
        )}
      </div>
    </div>
  );
}

export default function Graph() {
  return (
    <ReactFlowProvider>
      <GraphInner />
    </ReactFlowProvider>
  );
}
