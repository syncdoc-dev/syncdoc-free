import { useEffect, useState } from "react";
import { Database, FileText, Activity, AlertTriangle, GitBranch, TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import { getAnalytics } from "../api/client";
import type { AnalyticsData } from "../types";
import { useAuth } from "../context/AuthContext";
import UpgradeBadge from "../components/UpgradeBadge";

function SimpleLineChart({
  data,
  lines,
  height = 120,
}: {
  data: { label: string; [key: string]: number | string }[];
  lines: { key: string; color: string; label: string }[];
  height?: number;
}) {
  const max = Math.max(
    ...data.flatMap((d) => lines.map((l) => Number(d[l.key]) || 0)),
    1
  );
  const width = 100;
  const points: { [key: string]: string } = {};

  lines.forEach((line) => {
    const coords = data
      .map((d, i) => {
        const x = (i / (data.length - 1 || 1)) * width;
        const y = height - 20 - ((Number(d[line.key]) || 0) / max) * (height - 30);
        return `${x},${y}`;
      })
      .join(" ");
    points[line.key] = coords;
  });

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
      {lines.map((line) => (
        <polyline
          key={line.key}
          points={points[line.key]}
          fill="none"
          stroke={line.color}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="opacity-80"
        />
      ))}
      <line x1={0} y1={height - 20} x2={width} y2={height - 20} stroke="#334155" strokeWidth={1} />
    </svg>
  );
}

function StatCard({
  label,
  value,
  subValue,
  icon: Icon,
  color,
  trend,
}: {
  label: string;
  value: string | number;
  subValue?: string;
  icon: React.ElementType;
  color: string;
  trend?: "up" | "down" | "neutral";
}) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-[var(--text-secondary)]">{label}</span>
        <div className={`rounded-lg p-2 ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="mt-3 flex items-end gap-2">
        <p className="text-3xl font-semibold text-[var(--text-white)]">{value}</p>
        {trend && (
          trend === "up" ? (
            <TrendingUp className="w-4 h-4 text-emerald-400 mb-1" />
          ) : trend === "down" ? (
            <TrendingDown className="w-4 h-4 text-red-400 mb-1" />
          ) : null
        )}
      </div>
      {subValue && <p className="text-xs text-[var(--text-muted)] mt-1">{subValue}</p>}
    </div>
  );
}

function toolBadge(type: string | null | undefined) {
  if (!type) return null;
  const colors: Record<string, string> = {
    terraform: "bg-purple-500/20 text-purple-400 border-purple-500/30",
    docker: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    ansible: "bg-red-500/20 text-red-400 border-red-500/30",
    git: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    ci_cd: "bg-green-500/20 text-green-400 border-green-500/30",
  };
  const color = colors[type] ?? "bg-slate-500/20 text-slate-400 border-slate-500/30";
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded border ${color}`}>
      {type}
    </span>
  );
}

export default function Analytics() {
  const { hasFeature } = useAuth();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [days, setDays] = useState(30);
  const analyticsLicensed = hasFeature("analytics");

  useEffect(() => {
    if (!analyticsLicensed) {
      setLoading(false);
      setData(null);
      return;
    }
    setLoading(true);
    setError("");
    getAnalytics(days)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [days, analyticsLicensed]);

  if (!analyticsLicensed) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <UpgradeBadge />
        </div>
        <p className="mt-2 text-sm text-amber-100/90">
          Analytics is available on Pro and above. Upgrade your license to unlock usage trends,
          sync frequency, and coverage reporting.
        </p>
      </div>
    );
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-red-950/20 border border-red-900/50 text-red-400 text-sm">
        Error loading analytics: {error}
      </div>
    );
  }

  if (!data) return null;

  const { usage_stats, sync_frequency, drift_trends, page_coverage } = data;

  const syncChartData = sync_frequency.map((s) => ({
    label: formatDate(s.date),
    successful: s.successful,
    failed: s.failed,
  }));

  const driftChartData = drift_trends.map((d) => ({
    label: formatDate(d.date),
    detected: d.detected,
    resolved: d.resolved,
  }));

  return (
    <>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-slate-400 mt-1">
            Usage statistics, sync frequency, drift trends, and page coverage
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:outline-none focus:border-violet-500"
        >
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Usage Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Sources"
          value={usage_stats.total_sources}
          subValue={`${usage_stats.sources_synced_this_week} synced this week`}
          icon={Database}
          color="bg-[var(--accent-bg)] text-[var(--accent-icon)]"
        />
        <StatCard
          label="Infra Nodes"
          value={usage_stats.total_nodes}
          icon={GitBranch}
          color="bg-blue-500/15 text-blue-400"
        />
        <StatCard
          label="Doc Pages"
          value={usage_stats.total_pages}
          subValue={`${usage_stats.pages_created_this_week} created this week`}
          icon={FileText}
          color="bg-amber-500/15 text-amber-400"
        />
        <StatCard
          label="Drift Events"
          value={usage_stats.total_drift_events}
          subValue={`${usage_stats.drift_events_this_week} this week`}
          icon={AlertTriangle}
          color="bg-red-500/15 text-red-400"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Sync Frequency */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-violet-400" />
              Sync Frequency
            </h2>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Successful
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-400" />
                Failed
              </span>
            </div>
          </div>
          {syncChartData.length > 0 ? (
            <SimpleLineChart
              data={syncChartData}
              lines={[
                { key: "successful", color: "#34d399", label: "Successful" },
                { key: "failed", color: "#f87171", label: "Failed" },
             ]}
              height={150}
            />
          ) : (
            <div className="h-[150px] flex items-center justify-center text-slate-500 text-sm">
              No sync data available
            </div>
          )}
        </div>

        {/* Drift Trends */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Drift Trends
            </h2>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                Detected
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Resolved
              </span>
            </div>
          </div>
          {driftChartData.length > 0 ? (
            <SimpleLineChart
              data={driftChartData}
              lines={[
                { key: "detected", color: "#fbbf24", label: "Detected" },
                { key: "resolved", color: "#34d399", label: "Resolved" },
              ]}
              height={150}
            />
          ) : (
            <div className="h-[150px] flex items-center justify-center text-slate-500 text-sm">
              No drift data available
            </div>
          )}
        </div>
      </div>

      {/* Page Coverage by Source */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
          <h2 className="font-semibold text-white flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-blue-400" />
            Page Coverage by Source
          </h2>
          <div className="flex items-center gap-4 text-xs text-slate-400">
            <span>Nodes</span>
            <span>Pages</span>
            <span>Drift</span>
          </div>
        </div>

        {page_coverage.sources.length === 0 ? (
          <p className="px-5 py-8 text-center text-slate-500">
            No sources configured yet. Add a source to see coverage metrics.
          </p>
        ) : (
          <div className="divide-y divide-[var(--border)]">
            {page_coverage.sources.map((source) => (
              <div
                key={source.source_id}
                className="flex items-center justify-between px-5 py-4 hover:bg-[var(--hover-bg)] transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Database className="w-4 h-4 text-slate-500 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm text-white truncate max-w-[300px]" title={source.source_name}>
                      {source.source_name}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      {toolBadge(source.source_type)}
                      {source.last_synced && (
                        <span className="text-xs text-slate-500">
                          Last sync: {new Date(source.last_synced).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-8 text-sm">
                  <span className="text-slate-400 w-12 text-right">{source.node_count}</span>
                  <span className="text-slate-400 w-12 text-right">{source.page_count}</span>
                  <span className={`w-12 text-right ${source.drift_count > 0 ? "text-amber-400" : "text-slate-500"}`}>
                    {source.drift_count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Coverage Summary */}
        {page_coverage.total_pages > 0 && (
          <div className="px-5 py-4 border-t border-[var(--border)] bg-slate-900/30">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-6">
                <span className="text-slate-400">
                  Total Pages: <span className="text-white font-medium">{page_coverage.total_pages}</span>
                </span>
                <span className="text-slate-400">
                  With Source: <span className="text-white font-medium">{page_coverage.pages_with_source}</span>
                </span>
              </div>
              <div className="flex items-center gap-6">
                <span className="text-slate-400">
                  Auto-generated: <span className="text-blue-400 font-medium">{page_coverage.auto_generated}</span>
                </span>
                <span className="text-slate-400">
                  Manually edited: <span className="text-amber-400 font-medium">{page_coverage.manually_edited}</span>
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
