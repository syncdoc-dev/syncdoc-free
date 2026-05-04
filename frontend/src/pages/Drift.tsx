import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, CheckCircle, Clock, ChevronDown, ChevronRight } from "lucide-react";
import { getDriftEvents, getDriftStats, resolveDriftEvent } from "../api/client";
import type { DriftEvent, DriftStats } from "../types";

function kindLabel(kind: string | null): string {
  if (!kind) return "unknown";
  return kind.replace(/^tf:/, "").replace(/_/g, " ");
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

function DiffView({ diff }: { diff: DriftEvent["diff_json"] }) {
  const rows: { field: string; before: React.ReactNode; after: React.ReactNode }[] = [];

  if (diff.changed) {
    for (const [key, val] of Object.entries(diff.changed)) {
      rows.push({
        field: key,
        before: (
          <span className="text-red-300/80">
            {typeof val.old === "object" ? JSON.stringify(val.old) : String(val.old)}
          </span>
        ),
        after: (
          <span className="text-emerald-300/80">
            {typeof val.new === "object" ? JSON.stringify(val.new) : String(val.new)}
          </span>
        ),
      });
    }
  }

  if (diff.removed) {
    for (const [key, val] of Object.entries(diff.removed)) {
      rows.push({
        field: key,
        before: (
          <span className="text-red-300/80">
            {typeof val === "object" ? JSON.stringify(val) : String(val)}
          </span>
        ),
        after: <span className="text-slate-600">—</span>,
      });
    }
  }

  if (diff.added) {
    for (const [key, val] of Object.entries(diff.added)) {
      rows.push({
        field: key,
        before: <span className="text-slate-600">—</span>,
        after: (
          <span className="text-emerald-300/80">
            {typeof val === "object" ? JSON.stringify(val) : String(val)}
          </span>
        ),
      });
    }
  }

  if (rows.length === 0) {
    return <p className="text-slate-500 text-sm">No changes</p>;
  }

  return (
    <table className="w-full text-sm font-mono">
      <thead>
        <tr className="text-left text-slate-500 text-xs border-b border-slate-800">
          <th className="pb-2 font-medium">Field</th>
          <th className="pb-2 font-medium">Before</th>
          <th className="pb-2 font-medium">After</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.field} className="border-b border-slate-800/50 last:border-0">
            <td className="py-2 pr-4 text-slate-400 whitespace-pre-wrap">{row.field}</td>
            <td className="py-2 pr-4 whitespace-pre-wrap">{row.before}</td>
            <td className="py-2 whitespace-pre-wrap">{row.after}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DriftCard({
  event,
  onResolve,
}: {
  event: DriftEvent;
  onResolve: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const isResolved = event.resolved === 1;
  const changeCount =
    Object.keys(event.diff_json.added || {}).length +
    Object.keys(event.diff_json.removed || {}).length +
    Object.keys(event.diff_json.changed || {}).length;

  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        isResolved
          ? "border-slate-800 bg-slate-900/30"
          : "border-amber-800/50 bg-amber-950/20"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-start gap-3 text-left flex-1 min-w-0"
        >
          <div className="mt-0.5">
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-slate-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-500" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              {isResolved ? (
                <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
              )}
              <span className="font-semibold text-white truncate">
                {event.node_name || event.node_id}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 shrink-0">
                {kindLabel(event.node_kind)}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {timeAgo(event.detected_at)}
              </span>
              <span>
                {changeCount} {changeCount === 1 ? "change" : "changes"}
              </span>
              {isResolved && event.resolution_notes && (
                <span className="text-slate-600 italic truncate">
                  {event.resolution_notes}
                </span>
              )}
            </div>
          </div>
        </button>

        {!isResolved && (
          <button
            onClick={() => onResolve(event.id)}
            className="shrink-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
          >
            Resolve
          </button>
        )}
      </div>

      {expanded && (
        <div className="mt-4 ml-7 p-3 rounded-lg bg-slate-950/50 border border-slate-800">
          <DiffView diff={event.diff_json} />
        </div>
      )}
    </div>
  );
}

export default function Drift() {
  const [searchParams] = useSearchParams();
  const sourceFilter = searchParams.get("source") || undefined;

  const [events, setEvents] = useState<DriftEvent[]>([]);
  const [stats, setStats] = useState<DriftStats | null>(null);
  const [filter, setFilter] = useState<"all" | "unresolved" | "resolved">("all");
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    const resolvedParam =
      filter === "unresolved" ? 0 : filter === "resolved" ? 1 : undefined;
    Promise.all([getDriftEvents(sourceFilter, resolvedParam), getDriftStats()])
      .then(([evts, st]) => {
        setEvents(evts);
        setStats(st);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [filter, sourceFilter]);

  const handleResolve = async (id: string) => {
    await resolveDriftEvent(id);
    loadData();
  };

  return (
    <>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Drift Detection</h1>
          <p className="text-slate-400 mt-1">
            Infrastructure changes detected between sync runs
          </p>
        </div>
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-center">
            <p className="text-2xl font-semibold text-white">{stats.total}</p>
            <p className="text-sm text-slate-400">Total Events</p>
          </div>
          <div className="rounded-xl border border-amber-900/50 bg-amber-950/20 p-4 text-center">
            <p className="text-2xl font-semibold text-amber-400">
              {stats.unresolved}
            </p>
            <p className="text-sm text-slate-400">Unresolved</p>
          </div>
          <div className="rounded-xl border border-emerald-900/50 bg-emerald-950/20 p-4 text-center">
            <p className="text-2xl font-semibold text-emerald-400">
              {stats.resolved}
            </p>
            <p className="text-sm text-slate-400">Resolved</p>
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-1 mb-6 p-1 rounded-lg bg-slate-900/50 border border-slate-800 w-fit">
        {(["all", "unresolved", "resolved"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1.5 text-sm rounded-md transition-colors capitalize ${
              filter === f
                ? "bg-slate-700 text-white font-medium"
                : "text-slate-400 hover:text-slate-300"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Event list */}
      {loading ? (
        <div className="flex items-center justify-center h-40">
          <div className="w-6 h-6 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : events.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 text-slate-500">
          <AlertTriangle className="w-10 h-10 mb-3" />
          <p>No drift events found</p>
          <p className="text-sm mt-1">
            Drift is detected when infrastructure changes between syncs
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {events.map((event) => (
            <DriftCard
              key={event.id}
              event={event}
              onResolve={handleResolve}
            />
          ))}
        </div>
      )}
    </>
  );
}
