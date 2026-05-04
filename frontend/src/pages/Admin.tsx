import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  Database,
  Server as ServerIcon,
  Settings,
  Package,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  GitBranch,
  RefreshCw,
} from "lucide-react";
import { getApiBase } from "../api/client";

type SystemStatus = {
  status: string;
  timestamp: string;
  version: string;
};

type ComponentStatus = {
  name: string;
  status: string;
  details: string | null;
};

type DbStats = {
  total_sources: number;
  total_nodes: number;
  total_pages: number;
  total_drift_events: number;
  total_sync_runs: number;
};

type AdminResponse = {
  system: SystemStatus;
  components: ComponentStatus[];
  database_stats: DbStats;
  settings_summary: Record<string, unknown>;
};

function componentIcon(status: string) {
  switch (status) {
    case "healthy":
      return <CheckCircle className="w-5 h-5 text-emerald-400" />;
    case "unhealthy":
      return <XCircle className="w-5 h-5 text-red-400" />;
    default:
      return <Clock className="w-5 h-5 text-slate-400" />;
  }
}

function StatsCard({
  icon: Icon,
  label,
  value,
  color = "text-white"
}: {
  icon: React.ElementType;
  label: string;
  value: number | string;
  color?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-slate-800">
          <Icon className="w-5 h-5 text-slate-400" />
        </div>
        <div>
          <p className="text-sm text-slate-400">{label}</p>
          <p className={`text-xl font-semibold ${color}`}>{value}</p>
        </div>
      </div>
    </div>
  );
}

function ComponentRow({ component }: { component: ComponentStatus }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-800/50 last:border-0">
      <div className="flex items-center gap-3">
        {componentIcon(component.status)}
        <span className="text-sm font-medium text-white capitalize">{component.name}</span>
      </div>
      <div className="text-right">
        <span className={`text-sm ${
          component.status === "healthy" ? "text-emerald-400" :
          component.status === "unhealthy" ? "text-red-400" : "text-slate-400"
        }`}>
          {component.status}
        </span>
        {component.details && (
          <p className="text-xs text-slate-500">{component.details}</p>
        )}
      </div>
    </div>
  );
}

export default function Admin() {
  const [data, setData] = useState<AdminResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = useCallback(() => {
    setLoading(true);
    setError("");
    fetch(`${getApiBase()}/admin/status`, {
      headers: {
        "Authorization": `Bearer ${localStorage.getItem("syncdoc_token")}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">System Status</h1>
          <p className="text-slate-400 mt-1">
            Admin panel for monitoring and debugging
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 rounded-lg bg-red-950/20 border border-red-900/50 text-red-400 text-sm">
          Error: {error}
        </div>
      )}

      {loading && !data ? (
        <div className="flex items-center justify-center h-40">
          <div className="w-6 h-6 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : data ? (
        <>
          {/* System Info */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-5 h-5 text-slate-400" />
              <h2 className="text-lg font-semibold text-white">System</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                <p className="text-sm text-slate-400">Status</p>
                <p className="text-xl font-semibold text-emerald-400 capitalize">{data.system.status}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                <p className="text-sm text-slate-400">Version</p>
                <p className="text-xl font-semibold text-white">{data.system.version}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                <p className="text-sm text-slate-400">Environment</p>
                <p className="text-xl font-semibold text-white capitalize">{data.settings_summary.environment as string}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                <p className="text-sm text-slate-400">LLM Provider</p>
                <p className="text-xl font-semibold text-white">{data.settings_summary.llm_provider as string}</p>
              </div>
            </div>
          </div>

          {/* Components */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-4">
              <ServerIcon className="w-5 h-5 text-slate-400" />
              <h2 className="text-lg font-semibold text-white">Components</h2>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
              {data.components.map((comp) => (
                <ComponentRow key={comp.name} component={comp} />
              ))}
            </div>
          </div>

          {/* Database Stats */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-4">
              <Database className="w-5 h-5 text-slate-400" />
              <h2 className="text-lg font-semibold text-white">Database</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <StatsCard icon={GitBranch} label="Sources" value={data.database_stats.total_sources} />
              <StatsCard icon={Package} label="Nodes" value={data.database_stats.total_nodes} />
              <StatsCard icon={FileText} label="Pages" value={data.database_stats.total_pages} />
              <StatsCard icon={AlertTriangle} label="Drift Events" value={data.database_stats.total_drift_events} color={data.database_stats.total_drift_events > 0 ? "text-amber-400" : "text-white"} />
              <StatsCard icon={Activity} label="Sync Runs" value={data.database_stats.total_sync_runs} />
            </div>
          </div>

          {/* Quick Links */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-4">
              <Settings className="w-5 h-5 text-slate-400" />
              <h2 className="text-lg font-semibold text-white">Quick Links</h2>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/sources"
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm text-white transition-colors"
              >
                Sources
              </Link>
              <Link
                to="/drift"
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm text-white transition-colors"
              >
                Drift
              </Link>
              <Link
                to="/audit"
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm text-white transition-colors"
              >
                Audit Log
              </Link>
              <Link
                to="/pages"
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm text-white transition-colors"
              >
                Pages
              </Link>
              <Link
                to="/graph"
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm text-white transition-colors"
              >
                Graph
              </Link>
            </div>
          </div>

          {/* Settings Summary */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Settings className="w-5 h-5 text-slate-400" />
              <h2 className="text-lg font-semibold text-white">Settings</h2>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(data.settings_summary).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-xs text-slate-500 capitalize">{key.replace(/_/g, " ")}</p>
                    <p className="text-sm text-white">
                      {typeof value === "boolean" ? (value ? "✓" : "✗") : String(value)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
