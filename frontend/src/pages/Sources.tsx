import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Container,
  Database,
  FolderSearch,
  GitBranch,
  Info,
  Key,
  LoaderCircle,
  Plus,
  RefreshCw,
  Terminal,
  Trash2,
} from "lucide-react";
import {
  createCredential,
  createSource,
  deleteCredential,
  deleteSource,
  getAllSyncRuns,
  getSettings,
  getSources,
  getSyncRuns,
  inspectSource,
  listCredentials,
  syncSource,
  type SyncRunWithSource,
} from "../api/client";
import type { AppSettings, Source, SourceInspection } from "../types";
import { useAuth } from "../context/AuthContext";
import UpgradeBadge from "../components/UpgradeBadge";

const TYPE_ICONS: Record<string, React.ElementType> = {
  terraform: Database,
  docker: Container,
  git: GitBranch,
  ansible: Terminal,
  ci_cd: RefreshCw,
};

const TYPE_COLORS: Record<string, string> = {
  terraform: "bg-violet-500/15 text-violet-400 border-violet-500/30",
  docker: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  git: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  ansible: "bg-red-500/15 text-red-400 border-red-500/30",
  ci_cd: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
};

const SOURCE_TYPE_INFO: Record<
  string,
  { label: string; summary: string; expectation: string; examples: string }
> = {
  terraform: {
    label: "Terraform",
    summary: "Recursively scans the repository for `.tf` and `.tfstate` files.",
    expectation: "Best for repos containing Terraform modules, stacks, or state snapshots.",
    examples: "Examples: `main.tf`, `modules/network/*.tf`, `terraform.tfstate`",
  },
  docker: {
    label: "Docker",
    summary: "Recursively scans for `docker-compose*.yml`, `compose.yml`, and `Dockerfile*`.",
    expectation: "Use this only when the repo actually contains Docker compose files or Dockerfiles.",
    examples: "Examples: `docker-compose.yml`, `apps/api/Dockerfile`",
  },
  ansible: {
    label: "Ansible",
    summary:
      "Recursively scans for inventories, playbooks, `roles/`, `group_vars/`, and `host_vars/`.",
    expectation: "Best for Ansible repos with playbooks or inventory-driven automation.",
    examples: "Examples: `inventory/hosts.yml`, `playbooks/site.yml`, `roles/nginx/`",
  },
  git: {
    label: "Git",
    summary:
      "Clones the repo and recursively extracts Terraform, Docker, Ansible, and CI/CD definitions it finds inside.",
    expectation:
      "Use this for most real repositories, especially monorepos or repos that mix infrastructure and delivery pipelines.",
    examples:
      "Examples: repos with `.github/workflows/`, `.gitlab-ci.yml`, Terraform modules, Dockerfiles, or Ansible playbooks",
  },
  ci_cd: {
    label: "CI/CD",
    summary: "Pipeline-specific connector for GitHub Actions and GitLab CI files.",
    expectation: "Advanced option. Most users should add the repo as `git` and let SyncDoc extract CI/CD automatically.",
    examples: "Use `git` unless you explicitly want a pipeline-only source.",
  },
};

type CredentialSummary = { id: string; credential_type: string; created_at: string };

export default function Sources() {
  const { user, entitlements, hasFeature, getLimit } = useAuth();
  const canEdit = user?.role !== "viewer";
  const [sources, setSources] = useState<Source[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ type: "terraform", url: "" });
  const [syncing, setSyncing] = useState<Set<string>>(new Set());
  const [expandedSource, setExpandedSource] = useState<string | null>(null);
  const [syncErrors, setSyncErrors] = useState<Record<string, string>>({});
  const [credentials, setCredentials] = useState<Record<string, CredentialSummary[]>>({});
  const [credForm, setCredForm] = useState<{
    sourceId: string;
    type: string;
    value: string;
  } | null>(null);
  const [credentialsLoaded, setCredentialsLoaded] = useState(false);
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [syncRuns, setSyncRuns] = useState<SyncRunWithSource[]>([]);
  const [inspection, setInspection] = useState<SourceInspection | null>(null);
  const [inspectionError, setInspectionError] = useState<string | null>(null);
  const [inspectionLoading, setInspectionLoading] = useState(false);
  const [addingSource, setAddingSource] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const sourceLimit = getLimit("sources");
  const sourceLimitReached = sourceLimit !== null && sources.length >= sourceLimit;
  const aiDocsLicensed = hasFeature("ai_docs");
  const semanticSearchLicensed = hasFeature("semantic_search");
  const selectedTypeInfo = SOURCE_TYPE_INFO[form.type] ?? SOURCE_TYPE_INFO.terraform;
  const canCheckSource = form.url.trim().length > 0;

  const load = async () => {
    const [fetchedSources, fetchedRuns] = await Promise.all([getSources(), getAllSyncRuns(50)]);
    setSources(fetchedSources);
    setSyncRuns(fetchedRuns);

    const allCredentials: Record<string, CredentialSummary[]> = {};
    await Promise.all(
      fetchedSources.map(async (source) => {
        try {
          const result = await listCredentials(source.id);
          allCredentials[source.id] = result.credentials;
        } catch {
          allCredentials[source.id] = [];
        }
      })
    );
    setCredentials(allCredentials);
    setCredentialsLoaded(true);
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      void getAllSyncRuns(50)
        .then(setSyncRuns)
        .catch(() => {});
    }, 5000);

    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    getSettings()
      .then((settings) => setAppSettings(settings))
      .catch((err) =>
        setSettingsError(err instanceof Error ? err.message : "Failed to load settings")
      );
  }, []);

  useEffect(() => {
    setInspection(null);
    setInspectionError(null);
    setAddError(null);
  }, [form.type, form.url]);

  const handleInspect = async () => {
    if (!canCheckSource) return null;
    setInspectionLoading(true);
    setInspectionError(null);
    setAddError(null);
    try {
      const result = await inspectSource({ type: form.type, url: form.url.trim() });
      setInspection(result);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Source inspection failed";
      setInspection(null);
      setInspectionError(message);
      return null;
    } finally {
      setInspectionLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!form.url.trim()) return;
    setAddingSource(true);
    setAddError(null);
    const inspected = await handleInspect();
    if (!inspected?.ok) {
      setAddingSource(false);
      if (!inspected && !inspectionError) {
        setAddError("Unable to validate this source.");
      } else if (inspected && !inspected.ok) {
        setAddError(inspected.summary);
      }
      return;
    }

    try {
      await createSource({ type: form.type, url: form.url.trim() });
      setForm({ type: "terraform", url: "" });
      setInspection(null);
      setInspectionError(null);
      setShowAdd(false);
      await load();
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Failed to add source");
    } finally {
      setAddingSource(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSource(id);
    } catch (err) {
      alert(`Delete failed: ${err instanceof Error ? err.message : err}`);
    }
    load();
  };

  const handleSync = async (id: string) => {
    setSyncing((prev) => new Set(prev).add(id));
    try {
      await syncSource(id);
    } finally {
      setTimeout(async () => {
        setSyncing((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        load();
        try {
          const runs = await getSyncRuns(id);
          if (runs.length > 0) {
            const latest = runs[0];
            if (latest.status === "failed" && latest.error_message) {
              setSyncErrors((prev) => ({ ...prev, [id]: latest.error_message! }));
            } else {
              setSyncErrors((prev) => {
                const next = { ...prev };
                delete next[id];
                return next;
              });
            }
          }
        } catch {
          // ignore sync run fetch errors
        }
      }, 2000);
    }
  };

  const handleToggleExpand = async (sourceId: string) => {
    if (expandedSource === sourceId) {
      setExpandedSource(null);
      return;
    }
    setExpandedSource(sourceId);
    setCredForm({ sourceId, type: "token", value: "" });
    if (!credentials[sourceId] && credentialsLoaded) {
      try {
        const result = await listCredentials(sourceId);
        setCredentials((prev) => ({ ...prev, [sourceId]: result.credentials }));
      } catch {
        setCredentials((prev) => ({ ...prev, [sourceId]: [] }));
      }
    }
  };

  const handleAddCredential = async () => {
    if (!credForm || !credForm.value.trim()) return;
    try {
      await createCredential(credForm.sourceId, {
        credential_type: credForm.type,
        secret_value: credForm.value,
      });
      setCredForm({ ...credForm, value: "" });
      const result = await listCredentials(credForm.sourceId);
      setCredentials((prev) => ({ ...prev, [credForm.sourceId]: result.credentials }));
    } catch (err) {
      alert(`Failed to save credential: ${err instanceof Error ? err.message : err}`);
    }
  };

  const handleDeleteCredential = async (sourceId: string, credId: string) => {
    try {
      await deleteCredential(sourceId, credId);
      const result = await listCredentials(sourceId);
      setCredentials((prev) => ({ ...prev, [sourceId]: result.credentials }));
    } catch (err) {
      alert(`Failed to delete credential: ${err instanceof Error ? err.message : err}`);
    }
  };

  const featureCards = useMemo(() => {
    const hasLlmKey = appSettings && !!appSettings.llm_api_key;
    return [
      {
        title: "LLM Page Generation",
        enabled: !!hasLlmKey && aiDocsLicensed,
        on: "Docs are generated during source syncs.",
        off: aiDocsLicensed
          ? "Add an LLM key to enable page generation."
          : "Upgrade your license to enable AI doc generation.",
      },
      {
        title: "Semantic Search",
        enabled: !!hasLlmKey && semanticSearchLicensed,
        on: "Embedding-based search is enabled.",
        off: semanticSearchLicensed
          ? "Add an LLM key to enable semantic search."
          : "Upgrade your license to enable semantic search.",
      },
      {
        title: "Graph + Drift",
        enabled: true,
        on: "Graph and drift detection are active.",
        off: "",
      },
    ];
  }, [aiDocsLicensed, appSettings, semanticSearchLicensed]);

  const activeRunsBySource = useMemo(
    () =>
      new Map(
        syncRuns
          .filter((run) => run.status === "queued" || run.status === "in_progress")
          .map((run) => [run.source_id, run])
      ),
    [syncRuns]
  );
  const docsGenerationAvailable = Boolean(appSettings?.llm_api_key) && aiDocsLicensed;

  return (
    <>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-[var(--text-white)]">Sources</h1>
            {sourceLimitReached && <UpgradeBadge />}
          </div>
          <p className="mt-1 text-[var(--text-secondary)]">Manage your IaC source repositories</p>
          {sourceLimit !== null && (
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              {sources.length}/{sourceLimit} sources on the {entitlements?.plan ?? "free"} plan
            </p>
          )}
        </div>
        {canEdit && (
          <button
            onClick={() => setShowAdd(!showAdd)}
            disabled={sourceLimitReached}
            className="flex items-center gap-2 rounded-lg bg-[var(--accent-strong)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-50"
            title={sourceLimitReached ? "Upgrade license to add more sources" : "Add Source"}
          >
            <Plus className="h-4 w-4" />
            Add Source
          </button>
        )}
      </div>

      {canEdit && showAdd && (
        <div className="mb-6 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h3 className="mb-4 font-medium text-[var(--text-white)]">New Source</h3>
          {sourceLimitReached && (
            <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
              This license has reached its source limit. Upgrade the license to add more sources.
            </div>
          )}

          <div className="mb-4 rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-4">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-[var(--accent-icon)]" />
              <h4 className="text-sm font-semibold text-[var(--text-white)]">
                {selectedTypeInfo.label} source rules
              </h4>
            </div>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">{selectedTypeInfo.summary}</p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">{selectedTypeInfo.expectation}</p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">{selectedTypeInfo.examples}</p>
          </div>

          <div className="flex flex-col gap-3 lg:flex-row">
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
              className="rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent-strong)] focus:outline-none"
              disabled={sourceLimitReached || addingSource}
            >
              {["terraform", "docker", "ansible", "git"].map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Repository URL or path..."
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && void handleAdd()}
              className="flex-1 rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-strong)] focus:outline-none"
              disabled={sourceLimitReached || addingSource}
            />
            <button
              onClick={() => void handleInspect()}
              disabled={!canCheckSource || inspectionLoading || addingSource}
              className="flex items-center justify-center gap-2 rounded-lg border border-[var(--border-light)] px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {inspectionLoading ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <FolderSearch className="h-4 w-4" />
              )}
              Check
            </button>
            <button
              onClick={() => void handleAdd()}
              disabled={!canEdit || sourceLimitReached || addingSource}
              className="rounded-lg bg-[var(--accent-strong)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-50"
              title={canEdit ? "Add" : "Insufficient role"}
            >
              {addingSource ? "Adding..." : "Add"}
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="rounded-lg border border-[var(--border-light)] px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
            >
              Cancel
            </button>
          </div>

          {inspectionError && (
            <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {inspectionError}
            </div>
          )}
          {addError && (
            <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {addError}
            </div>
          )}
          {inspection && (
            <div
              className={`mt-4 rounded-xl border p-4 ${
                inspection.ok
                  ? "border-emerald-500/30 bg-emerald-500/10"
                  : "border-amber-500/30 bg-amber-500/10"
              }`}
            >
              <div className="flex items-center gap-2">
                {inspection.ok ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-amber-400" />
                )}
                <p className="text-sm font-medium text-[var(--text-white)]">{inspection.summary}</p>
              </div>
              {inspection.detected_types.length > 0 && (
                <p className="mt-2 text-xs text-[var(--text-secondary)]">
                  Detected types in repo: {inspection.detected_types.join(", ")}
                </p>
              )}
              {inspection.matched_files.length > 0 && (
                <div className="mt-3">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                    Matching files
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {inspection.matched_files.map((file) => (
                      <span
                        key={file}
                        className="rounded-full border border-[var(--border-light)] bg-[var(--bg-card)] px-2.5 py-1 text-xs text-[var(--text-secondary)]"
                      >
                        {file}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {inspection.warnings.length > 0 && (
                <div className="mt-3 space-y-1">
                  {inspection.warnings.map((warning) => (
                    <p key={warning} className="text-xs text-amber-100/90">
                      {warning}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="mb-6 grid grid-cols-1 gap-3 md:grid-cols-3">
        {featureCards.map((card) => (
          <div
            key={card.title}
            className={`rounded-xl border p-4 ${
              card.enabled
                ? "border-emerald-500/30 bg-emerald-500/10"
                : "border-amber-500/30 bg-amber-500/10"
            }`}
          >
            <div className="mb-2 flex items-center gap-2">
              {card.enabled ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <AlertCircle className="h-4 w-4 text-amber-400" />
              )}
              <h3 className="text-sm font-semibold text-[var(--text-white)]">{card.title}</h3>
              {!card.enabled &&
                (card.title === "LLM Page Generation" || card.title === "Semantic Search") && (
                  <UpgradeBadge label="Pro" />
                )}
            </div>
            <p className={`text-xs ${card.enabled ? "text-emerald-200/90" : "text-amber-200/90"}`}>
              {card.enabled ? card.on : card.off}
            </p>
            {!card.enabled && card.title === "LLM Page Generation" && (
              <p className="mt-1 text-xs text-amber-200/70">
                Infra graph and drift detection still run without an LLM key.
              </p>
            )}
          </div>
        ))}
      </div>

      {settingsError && (
        <div className="mb-6 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs text-amber-200/90">
          Unable to load LLM configuration. Feature indicators may be inaccurate.
        </div>
      )}

      {sources.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border-light)] py-16 text-center">
          <Database className="mx-auto mb-3 h-10 w-10 text-[var(--text-dimmed)]" />
          <p className="text-[var(--text-secondary)]">No sources registered yet</p>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Add a Terraform, Docker, Ansible, or Git source to get started. Git sources also extract CI/CD definitions automatically.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {sources.map((source) => {
            const Icon = TYPE_ICONS[source.type] || Database;
            const color = TYPE_COLORS[source.type] || "bg-slate-700/30 text-slate-400";
            const isExpanded = expandedSource === source.id;
            const syncError = syncErrors[source.id];
            const sourceCreds = credentials[source.id] ?? [];
            const shouldBeGreen = credentialsLoaded && sourceCreds.length > 0;
            const typeInfo = SOURCE_TYPE_INFO[source.type];
            const activeRun = activeRunsBySource.get(source.id);
            const isSyncActive = syncing.has(source.id) || Boolean(activeRun);

            return (
              <div
                key={source.id}
                className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg-card)]"
              >
                <div className="flex items-center gap-4 p-4">
                  <div className={`rounded-lg border p-2.5 ${color}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-[var(--text-white)]">
                      {source.url}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-3">
                      <span className="text-xs uppercase tracking-wide text-[var(--text-muted)]">
                        {source.type}
                      </span>
                      {source.last_synced && (
                        <span className="text-xs text-[var(--text-muted)]">
                          Last synced {new Date(source.last_synced).toLocaleString()}
                        </span>
                      )}
                    </div>
                    {typeInfo && (
                      <p className="mt-1 text-xs text-[var(--text-muted)]">{typeInfo.summary}</p>
                    )}
                    {isSyncActive && (
                      <div className="mt-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs text-blue-100">
                        <div className="flex items-center gap-2 font-medium text-blue-200">
                          <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                          {docsGenerationAvailable
                            ? "Sync is running. Graph updates and page generation are still in progress."
                            : "Sync is running. Graph updates are still in progress."}
                        </div>
                        <p className="mt-1 text-blue-100/85">
                          {docsGenerationAvailable
                            ? "Pages may appear a little after the sync starts. Check the Pages view if you want to watch them show up."
                            : "Add an LLM key if you also want docs to be generated during sync."}
                        </p>
                      </div>
                    )}
                    {syncError && (
                      <div className="mt-1.5 flex items-center gap-1.5">
                        <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 text-red-400" />
                        <span className="truncate text-xs text-red-400" title={syncError}>
                          {syncError.length > 80 ? `${syncError.slice(0, 80)}…` : syncError}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => void handleToggleExpand(source.id)}
                      disabled={!canEdit}
                      className={`rounded-lg p-2 transition-colors ${
                        isExpanded
                          ? "bg-[var(--hover-bg)] text-[var(--accent-icon)]"
                          : "text-[var(--text-secondary)] hover:bg-[var(--hover-bg)] hover:text-[var(--accent-icon)]"
                      }`}
                      title={canEdit ? "Manage credentials" : "Insufficient role"}
                    >
                      <Key
                        className={`h-4 w-4 ${
                          shouldBeGreen ? "text-emerald-400" : "text-[var(--text-secondary)]"
                        }`}
                      />
                    </button>
                    <button
                      onClick={() => void handleSync(source.id)}
                      disabled={isSyncActive || !canEdit}
                      className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--accent-icon)] disabled:opacity-50"
                      title={canEdit ? "Sync" : "Insufficient role"}
                    >
                      <RefreshCw className={`h-4 w-4 ${isSyncActive ? "animate-spin" : ""}`} />
                    </button>
                    <button
                      onClick={() => void handleDelete(source.id)}
                      disabled={!canEdit}
                      className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--hover-bg)] hover:text-red-400 disabled:opacity-50"
                      title={canEdit ? "Delete" : "Insufficient role"}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="space-y-3 border-t border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3">
                    <div className="rounded-lg border border-[var(--border-light)] bg-[var(--bg-card)] p-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                        How this source works
                      </p>
                      <p className="mt-2 text-sm text-[var(--text-secondary)]">
                        {typeInfo?.summary}
                      </p>
                      <p className="mt-1 text-xs text-[var(--text-muted)]">
                        {typeInfo?.expectation}
                      </p>
                    </div>

                    <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                      Credentials
                    </p>

                    {sourceCreds.length === 0 && credentialsLoaded ? (
                      <p className="text-xs text-[var(--text-muted)]">No credentials stored.</p>
                    ) : sourceCreds.length > 0 ? (
                      <div className="space-y-1.5">
                        {sourceCreds.map((cred) => (
                          <div
                            key={cred.id}
                            className="flex items-center gap-3 rounded-lg border border-[var(--border-light)] bg-[var(--bg-card)] px-3 py-2"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 text-emerald-400" />
                            <span className="text-xs font-medium text-[var(--text-primary)]">
                              {cred.credential_type}
                            </span>
                            <span className="font-mono text-xs text-[var(--text-muted)]">••••••••</span>
                            <span className="ml-auto text-xs text-[var(--text-muted)]">
                              {new Date(cred.created_at).toLocaleDateString()}
                            </span>
                            <button
                              onClick={() => void handleDeleteCredential(source.id, cred.id)}
                              disabled={!canEdit}
                              className="rounded p-1 text-[var(--text-muted)] transition-colors hover:text-red-400 disabled:opacity-50"
                              title={canEdit ? "Remove credential" : "Insufficient role"}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-[var(--text-muted)]">Loading credentials...</p>
                    )}

                    {credForm && credForm.sourceId === source.id && (
                      <div className="flex gap-2 pt-1">
                        <select
                          value={credForm.type}
                          onChange={(e) => setCredForm({ ...credForm, type: e.target.value })}
                          className="rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-2 py-1.5 text-xs text-[var(--text-primary)] focus:border-[var(--accent-strong)] focus:outline-none"
                        >
                          <option value="token">token</option>
                          <option value="ssh_key">ssh_key</option>
                        </select>
                        <textarea
                          placeholder={
                            credForm.type === "token"
                              ? "GitHub Personal Access Token..."
                              : "SSH private key..."
                          }
                          value={credForm.value}
                          onChange={(e) => setCredForm({ ...credForm, value: e.target.value })}
                          rows={1}
                          className="flex-1 resize-none rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-strong)] focus:outline-none"
                        />
                        <button
                          onClick={() => void handleAddCredential()}
                          disabled={!credForm.value.trim() || !canEdit}
                          className="rounded-lg bg-[var(--accent-strong)] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:opacity-50"
                        >
                          Save
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
