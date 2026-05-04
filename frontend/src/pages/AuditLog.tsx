import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Clock, CheckCircle, XCircle, Loader2, AlertTriangle, GitBranch } from "lucide-react";
import { getAllSyncRuns, getSources, type SyncRunWithSource } from "../api/client";
import type { Source } from "../types";

function statusIcon(status: string) {
  switch (status) {
    case "completed":
      return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    case "failed":
      return <XCircle className="w-4 h-4 text-red-400" />;
    case "in_progress":
      return <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />;
    case "pending":
      return <Clock className="w-4 h-4 text-slate-400" />;
    default:
      return <AlertTriangle className="w-4 h-4 text-slate-400" />;
  }
}

function statusLabel(status: string) {
  switch (status) {
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    case "in_progress":
      return "In Progress";
    case "pending":
      return "Pending";
    default:
      return status;
  }
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function toolBadge(type: string | null | undefined) {
  if (!type) return null;
  const colors: Record<string, string> = {
    terraform: "bg-purple-500/20 text-purple-400 border-purple-500/30",
    docker: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    ansible: "bg-red-500/20 text-red-400 border-red-500/30",
    git: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  };
  const color = colors[type] ?? "bg-slate-500/20 text-slate-400 border-slate-500/30";
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded border ${color}`}>
      {type}
    </span>
  );
}

export default function AuditLog() {
  const [runs, setRuns] = useState<SyncRunWithSource[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [filterSource, setFilterSource] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");

  const loadData = () => {
    setLoading(true);
    setError("");
    Promise.all([getAllSyncRuns(100, filterSource || undefined, filterStatus || undefined), getSources()])
      .then(([r, s]) => {
        setRuns(r);
        setSources(s);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [filterSource, filterStatus]);

  const stats = {
    total: runs.length,
    completed: runs.filter((r) => r.status === "completed").length,
    failed: runs.filter((r) => r.status === "failed").length,
    inProgress: runs.filter((r) => r.status === "in_progress").length,
  };

  return (
    <>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Audit Log</h1>
          <p className="text-slate-400 mt-1">
            Sync run history across all sources
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
          <p className="text-2xl font-semibold text-white">{stats.total}</p>
          <p className="text-sm text-slate-400">Total Runs</p>
        </div>
        <div className="rounded-xl border border-emerald-900/50 bg-emerald-950/20 p-4 text-center">
          <p className="text-2xl font-semibold text-emerald-400">{stats.completed}</p>
          <p className="text-sm text-slate-400">Completed</p>
        </div>
        <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-4 text-center">
          <p className="text-2xl font-semibold text-red-400">{stats.failed}</p>
          <p className="text-sm text-slate-400">Failed</p>
        </div>
        <div className="rounded-xl border border-amber-900/50 bg-amber-950/20 p-4 text-center">
          <p className="text-2xl font-semibold text-amber-400">{stats.inProgress}</p>
          <p className="text-sm text-slate-400">In Progress</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <select
          value={filterSource}
          onChange={(e) => setFilterSource(e.target.value)}
          className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:outline-none focus:border-violet-500"
        >
          <option value="">All Sources</option>
          {sources.map((s) => (
            <option key={s.id} value={s.id}>
              {s.url.split("/").pop()?.replace(".git", "")} ({s.type})
            </option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:outline-none focus:border-violet-500"
        >
          <option value="">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="in_progress">In Progress</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-4 rounded-lg bg-red-950/20 border border-red-900/50 text-red-400 text-sm">
          Error: {error}
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center h-40">
          <div className="w-6 h-6 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : runs.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 text-slate-500">
          <Clock className="w-10 h-10 mb-3" />
          <p>No sync runs found</p>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b border-slate-800">
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Started</th>
                <th className="px-4 py-3 font-medium">Duration</th>
                <th className="px-4 py-3 font-medium">Changes</th>
                <th className="px-4 py-3 font-medium">Drift</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const duration =
                  run.completed_at && run.started_at
                    ? Math.round(
                        (new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) /
                          1000
                      )
                    : null;
                return (
                  <tr
                    key={run.id}
                    className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {statusIcon(run.status)}
                        <span className="text-sm text-slate-300">{statusLabel(run.status)}</span>
                      </div>
                      {run.error_message && (
                        <p className="text-xs text-red-400 mt-1 truncate max-w-[200px]" title={run.error_message}>
                          {run.error_message}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <GitBranch className="w-4 h-4 text-slate-500" />
                        <span className="text-sm text-white">{run.source_name || run.source_id}</span>
                      </div>
                      {toolBadge(run.source_type)}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-slate-400" title={new Date(run.started_at).toLocaleString()}>
                        {timeAgo(run.started_at)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {duration !== null ? (
                        <span className="text-sm text-slate-400">
                          {duration < 60
                            ? `${duration}s`
                            : duration < 3600
                            ? `${Math.floor(duration / 60)}m ${duration % 60}s`
                            : `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`}
                        </span>
                      ) : run.status === "in_progress" ? (
                        <span className="text-sm text-amber-400">Running...</span>
                      ) : (
                        <span className="text-sm text-slate-500">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3 text-sm">
                        <span className="text-emerald-400">+{run.nodes_added}</span>
                        <span className="text-amber-400">~{run.nodes_updated}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {run.drift_count > 0 ? (
                        <Link
                          to={`/drift?source=${run.source_id}`}
                          className="text-sm text-amber-400 hover:text-amber-300 underline underline-offset-2"
                        >
                          {run.drift_count} detected
                        </Link>
                      ) : (
                        <span className="text-sm text-slate-500">None</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
