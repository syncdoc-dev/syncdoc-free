import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  Database,
  FileText,
  Network,
  Sparkles,
} from "lucide-react";
import { getSources, getPages, getHealth } from "../api/client";
import type { Source, Page } from "../types";

function StatCard({
  label,
  value,
  detail,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: React.ElementType;
  tone: "success" | "accent" | "info" | "warning";
}) {
  const toneStyles = {
    success: {
      iconBg: "var(--success-bg)",
      iconColor: "var(--success)",
      bar: "var(--success)",
    },
    accent: {
      iconBg: "var(--accent-bg)",
      iconColor: "var(--accent)",
      bar: "var(--accent)",
    },
    info: {
      iconBg: "var(--info-bg)",
      iconColor: "var(--info)",
      bar: "var(--info)",
    },
    warning: {
      iconBg: "var(--warning-bg)",
      iconColor: "var(--warning)",
      bar: "var(--warning)",
    },
  }[tone];

  return (
    <div className="app-panel relative overflow-hidden rounded-[24px] p-5">
      <div
        className="absolute inset-x-5 top-0 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${toneStyles.bar}, transparent)` }}
      />
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="app-kicker text-[11px] text-[var(--text-muted)]">{label}</div>
          <p className="mt-3 text-4xl font-semibold tracking-tight text-[var(--text-white)]">{value}</p>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">{detail}</p>
        </div>
        <div
          className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-[var(--border)]"
          style={{ background: toneStyles.iconBg, color: toneStyles.iconColor }}
        >
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [sources, setSources] = useState<Source[]>([]);
  const [pages, setPages] = useState<Page[]>([]);
  const [apiOk, setApiOk] = useState<boolean | null>(null);

  useEffect(() => {
    getSources().then(setSources).catch(() => setSources([]));
    getPages().then(setPages).catch(() => setPages([]));
    getHealth()
      .then(() => setApiOk(true))
      .catch(() => setApiOk(false));
  }, []);

  const synced = sources.filter((source) => source.last_synced).length;
  const latestPage = pages[0];

  return (
    <div className="space-y-5">
      <section className="app-panel overflow-hidden rounded-[32px]">
        <div className="brand-ribbon h-[2px] w-full opacity-90" />
        <div className="grid gap-6 px-6 py-7 lg:grid-cols-[1.2fr_0.8fr] lg:px-7 lg:py-8">
          <div>
            <div className="app-kicker text-sm text-[var(--accent)]">Live workspace</div>
            <h2 className="app-section-title mt-3 max-w-3xl text-4xl leading-none text-[var(--text-white)] sm:text-5xl">
              Docs, graph, and drift signals in one operator view.
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--text-secondary)]">
              This workspace now follows the darker editorial direction from the asset set:
              cooler surfaces, ribbon accents, stronger typography, and a graph-first control room feel.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                to="/graph"
                className="inline-flex items-center gap-2 rounded-full border border-[var(--border-bright)] bg-[var(--accent-bg)] px-4 py-2 text-sm font-medium text-[var(--text-white)] transition-colors hover:bg-[var(--hover-bg)]"
              >
                Open graph
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/sources"
                className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--bg-input)]/80 px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-white)]"
              >
                Manage sources
              </Link>
            </div>
          </div>

          <div className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-input)]/70 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="app-kicker text-[11px] text-[var(--text-muted)]">Snapshot</div>
                <div className="mt-2 text-lg font-medium text-[var(--text-white)]">
                  {apiOk === null ? "Checking platform state" : apiOk ? "Platform healthy" : "Platform unreachable"}
                </div>
              </div>
              <div
                className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-[var(--border)]"
                style={{
                  background: apiOk === false ? "var(--danger-bg)" : "var(--success-bg)",
                  color: apiOk === false ? "var(--danger)" : "var(--success)",
                }}
              >
                <Sparkles className="h-5 w-5" />
              </div>
            </div>

            <div className="mt-5 space-y-3">
              <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-[var(--text-secondary)]">Connected sources</span>
                  <span className="text-base font-semibold text-[var(--text-white)]">{sources.length}</span>
                </div>
              </div>
              <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-[var(--text-secondary)]">Generated pages</span>
                  <span className="text-base font-semibold text-[var(--text-white)]">{pages.length}</span>
                </div>
              </div>
              <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-[var(--text-secondary)]">Latest page</span>
                  <span className="max-w-[60%] truncate text-sm font-medium text-[var(--text-white)]">
                    {latestPage?.title ?? "None yet"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <StatCard
          label="API status"
          value={apiOk === null ? "..." : apiOk ? "Healthy" : "Down"}
          detail="Backend reachability and health endpoint"
          icon={Activity}
          tone={apiOk === false ? "warning" : "success"}
        />
        <StatCard
          label="Connected sources"
          value={sources.length}
          detail="Repositories and parsers feeding the workspace"
          icon={Database}
          tone="accent"
        />
        <StatCard
          label="Synced sources"
          value={synced}
          detail="Sources with at least one completed sync"
          icon={Network}
          tone="info"
        />
        <StatCard
          label="Generated pages"
          value={pages.length}
          detail="Runbooks and infra pages available to operators"
          icon={FileText}
          tone="warning"
        />
      </section>

      <section className="app-panel overflow-hidden rounded-[28px]">
        <div className="flex items-center justify-between gap-4 border-b border-[var(--border)] px-5 py-4 sm:px-6">
          <div>
            <div className="app-kicker text-[11px] text-[var(--text-muted)]">Recent output</div>
            <h3 className="mt-1 text-lg font-semibold text-[var(--text-white)]">Recent pages</h3>
          </div>
          <Link
            to="/pages"
            className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--bg-input)]/80 px-3 py-2 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-white)]"
          >
            View all
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        {pages.length === 0 ? (
          <div className="px-6 py-12 text-center text-[var(--text-muted)]">
            No pages yet. Add a source and trigger a sync to generate living documentation.
          </div>
        ) : (
          <ul className="divide-y divide-[var(--border)]">
            {pages.slice(0, 5).map((page) => (
              <li key={page.id}>
                <Link
                  to={`/pages/${page.id}`}
                  className="flex flex-col gap-3 px-5 py-4 transition-colors hover:bg-[var(--hover-bg)] sm:flex-row sm:items-center sm:justify-between sm:px-6"
                >
                  <div className="min-w-0">
                    <div className="text-base font-medium text-[var(--text-white)]">{page.title}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
                      <span className="rounded-full border border-[var(--border)] bg-[var(--bg-input)]/70 px-2.5 py-1">
                        v{page.version}
                      </span>
                      <span>Updated {new Date(page.updated_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <span className="inline-flex items-center gap-2 text-sm text-[var(--accent)]">
                    Open page
                    <ArrowRight className="h-4 w-4" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
