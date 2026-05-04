import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { ArrowLeft, Clock, Hash, Edit2, Save, X, RefreshCw } from "lucide-react";
import { getPage, getSources, updatePage, getPageWorkflow, regeneratePage } from "../api/client";
import type { Page, Source, PageWithWorkflow, WorkflowInfo } from "../types";
import { TOOL_COLORS } from "../components/InfraNode";
import WorkflowPanel from "../components/WorkflowPanel";
import { useAuth } from "../context/AuthContext";
import UpgradeBadge from "../components/UpgradeBadge";
import MermaidBlock from "../components/MermaidBlock";

const SOURCE_TYPE_TO_TOOL: Record<string, string> = {
  terraform: "tf",
  docker: "docker",
  ansible: "ansible",
  git: "git",
};

const MERMAID_START_RE =
  /^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|mindmap|timeline|gitGraph|quadrantChart|requirementDiagram|block-beta|C4Context|C4Container|C4Component|C4Dynamic|C4Deployment)\b/;

function normalizeLeadingMermaid(content: string): string {
  if (content.includes("```mermaid")) {
    return content;
  }

  const lines = content.split("\n");
  let start = 0;

  while (start < lines.length && !lines[start].trim()) {
    start += 1;
  }

  if (start >= lines.length) {
    return content;
  }

  const firstLine = lines[start].replace(/^\s{4}/, "").trim();
  if (!MERMAID_START_RE.test(firstLine)) {
    return content;
  }

  let end = start;
  while (end < lines.length) {
    const rawLine = lines[end];
    const normalizedLine = rawLine.replace(/^\s{4}/, "");
    if (!normalizedLine.trim()) {
      break;
    }
    end += 1;
  }

  const diagramLines = lines.slice(start, end).map((line) => line.replace(/^\s{4}/, ""));
  const prefix = lines.slice(0, start).join("\n");
  const suffix = lines.slice(end).join("\n");
  const fenced = `\`\`\`mermaid\n${diagramLines.join("\n")}\n\`\`\``;

  return [prefix, fenced, suffix].filter(Boolean).join("\n");
}

function resolveToolColor(page: Page | null, sources: Source[]): string | null {
  if (!page?.source_id) return null;
  const source = sources.find((s) => s.id === page.source_id);
  if (!source) return null;
  const toolKey = SOURCE_TYPE_TO_TOOL[source.type] ?? "other";
  return TOOL_COLORS[toolKey]?.hex ?? null;
}

export default function PageDetail() {
  const { user, hasFeature } = useAuth();
  const canEdit = user?.role !== "viewer";
  const canUseAiDocs = hasFeature("ai_docs");
  const { id } = useParams<{ id: string }>();
  const [page, setPage] = useState<Page | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowInfo | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const fetchWorkflow = () => {
    if (!id) return;
    getPageWorkflow(id)
      .then((data: PageWithWorkflow) => setWorkflow(data.workflow || null))
      .catch(() => setWorkflow(null));
  };

  useEffect(() => {
    if (!id) return;
    getPage(id)
      .then(setPage)
      .catch((e) => setError(e.message));
    getSources().then(setSources).catch(() => {});
    fetchWorkflow();
  }, [id]);

  const handleEdit = () => {
    if (page && canEdit) {
      setEditContent(page.content_md);
      setEditMode(true);
    }
  };

  const handleSave = async () => {
    if (!id || !page) return;
    setSaving(true);
    try {
      const updated = await updatePage(id, editContent);
      setPage({ ...updated, is_manually_edited: 1 });
      setEditMode(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditMode(false);
    setEditContent("");
  };

  const handleRegenerate = async () => {
    if (!id || !page || !page.source_id) return;
    setRegenerating(true);
    try {
      const updated = await regeneratePage(id);
      setPage(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to regenerate");
    } finally {
      setRegenerating(false);
    }
  };

  const toolColor = resolveToolColor(page, sources);
  const source = page?.source_id
    ? sources.find((s) => s.id === page.source_id)
    : null;
  const toolKey = source ? SOURCE_TYPE_TO_TOOL[source.type] ?? "other" : null;
  const toolLabel = toolKey ? TOOL_COLORS[toolKey]?.label : null;
  const normalizedContent = useMemo(
    () => (page ? normalizeLeadingMermaid(page.content_md) : ""),
    [page],
  );
  const markdownComponents = useMemo<Components>(
    () => ({
      code({ className, children, ...props }) {
        const match = /language-(\w+)/.exec(className || "");
        const language = match?.[1]?.toLowerCase();
        const codeContent = String(children).replace(/\n$/, "");

        if (language === "mermaid") {
          return <MermaidBlock chart={codeContent} />;
        }

        return (
          <code className={className} {...props}>
            {children}
          </code>
        );
      },
    }),
    [],
  );

  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-400">{error}</p>
        <Link to="/pages" className="text-[var(--accent-icon)] text-sm mt-2 inline-block">
          Back to pages
        </Link>
      </div>
    );
  }

  if (!page) {
    return (
      <div className="text-center py-16">
        <div className="w-6 h-6 border-2 border-[var(--accent-icon)] border-t-transparent rounded-full animate-spin mx-auto" />
      </div>
    );
  }

  return (
    <>
      <Link
        to="/pages"
        className="inline-flex items-center gap-1 text-sm text-[var(--text-secondary)] hover:text-[var(--accent-icon)] mb-6 transition-colors"
      >
        <ArrowLeft className="w-3 h-3" /> Back to pages
      </Link>

      <div
        className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] overflow-hidden"
        style={toolColor ? { borderTopColor: toolColor, borderTopWidth: 3 } : undefined}
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-[var(--border)] flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-[var(--text-white)]">{page.title}</h1>
            <div className="flex items-center gap-4 mt-2 text-xs text-[var(--text-muted)]">
              <span className="flex items-center gap-1">
                <Hash className="w-3 h-3" /> v{page.version}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />{" "}
                {new Date(page.updated_at).toLocaleString()}
              </span>
              {toolLabel && toolColor && (
                <span
                  className="px-1.5 py-0.5 rounded font-medium"
                  style={{
                    backgroundColor: `${toolColor}20`,
                    color: toolColor,
                    border: `1px solid ${toolColor}40`,
                  }}
                >
                  {toolLabel}
                </span>
              )}
              {page.is_manually_edited === 1 && (
                <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30">
                  manually edited
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {editMode ? (
              <>
                <button
                  onClick={handleCancel}
                  disabled={saving}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-input)] transition-colors disabled:opacity-50"
                >
                  <X className="w-3.5 h-3.5" /> Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-50"
                >
                  {saving ? (
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Save className="w-3.5 h-3.5" />
                  )}
                  Save
                </button>
              </>
            ) : (
              <>
                {page.source_id && (
                  <div className="flex items-center gap-2">
                    {!canUseAiDocs && <UpgradeBadge label="Pro" />}
                    <button
                      onClick={handleRegenerate}
                      disabled={!canEdit || regenerating || !canUseAiDocs}
                      title={
                        !canUseAiDocs
                          ? "Upgrade license to regenerate with AI docs"
                          : canEdit
                            ? "Regenerate from source"
                            : "Insufficient role"
                      }
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-input)] transition-colors disabled:opacity-50"
                    >
                      {regenerating ? (
                        <div className="w-3.5 h-3.5 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <RefreshCw className="w-3.5 h-3.5" />
                      )}
                      Regenerate
                    </button>
                  </div>
                )}
                <button
                  onClick={handleEdit}
                  disabled={!canEdit}
                  title={canEdit ? "Edit page" : "Insufficient role"}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-[var(--accent-icon)] hover:opacity-90 text-white transition-colors disabled:opacity-50"
                >
                  <Edit2 className="w-3.5 h-3.5" /> Edit
                </button>
              </>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          {editMode ? (
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full min-h-[400px] p-4 rounded-lg bg-[var(--bg-input)] border border-[var(--border)] text-[var(--text-white)] font-mono text-sm resize-y focus:outline-none focus:border-[var(--accent-icon)]"
              spellCheck={false}
            />
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-headings:text-[var(--text-white)] prose-a:text-[var(--accent-icon)] prose-code:text-[var(--accent)] prose-pre:bg-[var(--bg-input)] prose-pre:border prose-pre:border-[var(--border-light)] prose-table:border-collapse prose-th:border prose-th:border-[var(--border-light)] prose-th:bg-[var(--bg-input)] prose-th:px-3 prose-th:py-2 prose-th:text-[var(--text-secondary)] prose-td:border prose-td:border-[var(--border-light)] prose-td:px-3 prose-td:py-2">
              <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {normalizedContent}
              </Markdown>
            </div>
          )}
        </div>
      </div>

      {/* Workflow Panel */}
      {id && <WorkflowPanel pageId={id} workflow={workflow} onRefresh={fetchWorkflow} />}
    </>
  );
}
