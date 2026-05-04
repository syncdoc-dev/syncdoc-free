import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, LoaderCircle, Search } from "lucide-react";
import { getAllSyncRuns, getPages, getSettings, getSources, type SyncRunWithSource } from "../api/client";
import type { Page, Source, WorkflowState } from "../types";
import { TOOL_COLORS } from "../components/InfraNode";

/** Map source type to the tool color key used in TOOL_COLORS. */
const SOURCE_TYPE_TO_TOOL: Record<string, string> = {
  terraform: "tf",
  docker: "docker",
  ansible: "ansible",
  git: "git",
};

const WORKFLOW_COLORS: Record<string, string> = {
  draft: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  pending_review: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  under_review: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  approved: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  published: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  rejected: "bg-red-500/20 text-red-400 border-red-500/30",
  archived: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

function WorkflowBadge({ state }: { state: WorkflowState | undefined | null }) {
  if (!state) return null;
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${WORKFLOW_COLORS[state] || WORKFLOW_COLORS.draft}`}>
      {state.replace("_", " ")}
    </span>
  );
}

function ToolBadge({ sourceId, sources }: { sourceId: string | null; sources: Source[] }) {
  if (!sourceId) return null;
  const source = sources.find((s) => s.id === sourceId);
  if (!source) return null;
  const toolKey = SOURCE_TYPE_TO_TOOL[source.type] ?? "other";
  const color = TOOL_COLORS[toolKey] ?? TOOL_COLORS.other;
  return (
    <span
      className="text-[10px] px-1.5 py-0.5 rounded font-medium"
      style={{
        backgroundColor: `${color.hex}20`,
        color: color.hex,
        border: `1px solid ${color.hex}40`,
      }}
    >
      {color.label}
    </span>
  );
}

export default function Pages() {
  const [pages, setPages] = useState<Page[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [syncRuns, setSyncRuns] = useState<SyncRunWithSource[]>([]);
  const [search, setSearch] = useState("");
  const [llmReady, setLlmReady] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [pageItems, sourceItems, runs, settings] = await Promise.all([
          getPages(undefined, true),
          getSources(),
          getAllSyncRuns(20),
          getSettings().catch(() => null),
        ]);
        if (cancelled) return;
        setPages(pageItems);
        setSources(sourceItems);
        setSyncRuns(runs);
        if (settings) {
          setLlmReady(Boolean(settings.llm_api_key));
        } else {
          setLlmReady(null);
        }
      } catch {
        if (!cancelled) setLlmReady(null);
      }
    };

    load();
    const intervalId = window.setInterval(load, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  const filtered = pages.filter((p) =>
    p.title.toLowerCase().includes(search.toLowerCase()),
  );

  const pageSourceIds = new Set(pages.map((page) => page.source_id).filter(Boolean));
  const activeRunsBySource = new Map(
    syncRuns
      .filter((run) => run.status === "in_progress")
      .map((run) => [run.source_id, run])
  );
  const generatingSources = sources.filter(
    (source) => activeRunsBySource.has(source.id) && !pageSourceIds.has(source.id)
  );

  return (
    <>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-white)]">Pages</h1>
          <p className="text-[var(--text-secondary)] mt-1">
            Generated and curated documentation
          </p>
        </div>
      </div>

      {llmReady !== null && (
        <div
          className={`mb-6 rounded-xl border p-4 text-sm ${
            llmReady
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
              : "border-amber-500/30 bg-amber-500/10 text-amber-200"
          }`}
        >
          {llmReady ? (
            <span>
              LLM is configured. New pages are generated during source syncs.
            </span>
          ) : (
            <span>
              LLM API key is missing. Set your LLM API key in{" "}
              <Link className="underline" to="/settings">
                Settings
              </Link>{" "}
              to enable page generation.
            </span>
          )}
        </div>
      )}

      {generatingSources.length > 0 && (
        <div className="mb-6 rounded-xl border border-blue-500/30 bg-blue-500/10 p-4 text-sm text-blue-100">
          <div className="flex items-center gap-2 font-medium text-blue-200">
            <LoaderCircle className="h-4 w-4 animate-spin" />
            Documentation generation is in progress
          </div>
          <p className="mt-2 text-blue-100/90">
            SyncDoc is still building pages and graph data for these sources. Pages will appear
            here automatically when the sync finishes.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {generatingSources.map((source) => (
              <span
                key={source.id}
                className="rounded-full border border-blue-400/30 bg-blue-500/10 px-2.5 py-1 text-xs text-blue-100"
              >
                {source.type}: {source.url.split("/").pop() || source.url}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
        <input
          type="text"
          placeholder="Search pages..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] pl-10 pr-4 py-2.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-strong)]"
        />
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border-light)] py-16 text-center">
          <FileText className="w-10 h-10 text-[var(--text-dimmed)] mx-auto mb-3" />
          <p className="text-[var(--text-secondary)]">
            {search ? "No pages match your search" : "No pages yet"}
          </p>
          {!search && generatingSources.length > 0 && (
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              A sync is still running, so generated pages may appear shortly.
            </p>
          )}
        </div>
      ) : (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] divide-y divide-[var(--border)]">
          {filtered.map((page) => (
            <Link
              key={page.id}
              to={`/pages/${page.id}`}
              className="flex items-center justify-between px-5 py-4 hover:bg-[var(--hover-bg)] transition-colors"
            >
              <div className="flex items-center gap-3">
                <FileText className="w-4 h-4 text-[var(--text-muted)]" />
                <div>
                  <span className="text-sm font-medium text-[var(--text-white)]">
                    {page.title}
                  </span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-[var(--text-muted)]">
                      v{page.version}
                    </span>
                    <ToolBadge sourceId={page.source_id} sources={sources} />
                    <WorkflowBadge state={page.workflow?.state} />
                    {page.is_manually_edited === 1 && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30">
                        edited
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <span className="text-xs text-[var(--text-muted)]">
                {new Date(page.updated_at).toLocaleDateString()}
              </span>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
