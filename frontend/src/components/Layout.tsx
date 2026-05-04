import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Database,
  FileText,
  Network,
  AlertTriangle,
  Search,
  Settings,
  LogOut,
  History,
  Server,
  BarChart3,
  Building2,
  ShieldEllipsis,
  Menu,
  X,
  ChevronsLeft,
  ChevronsRight,
  ArrowUpRight,
} from "lucide-react";
import ThemeSwitcher from "./ThemeSwitcher";
import { useAuth } from "../context/AuthContext";
import { getProjectId, getProjects, setProjectId } from "../api/client";
import { useSyncEvents } from "../hooks/useSyncEvents";
import type { Project } from "../types";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/sources", label: "Sources", icon: Database },
  { to: "/pages", label: "Pages", icon: FileText },
  { to: "/graph", label: "Graph", icon: Network },
  { to: "/drift", label: "Drift", icon: AlertTriangle },
  { to: "/audit", label: "Audit Log", icon: History },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/organization", label: "Organization", icon: Building2 },
  { to: "/owner-explorer", label: "Owner Explorer", icon: ShieldEllipsis },
  { to: "/admin", label: "Admin", icon: Server },
  { to: "/search", label: "Search", icon: Search },
] as const;

const ADMIN_ROLES = new Set(["owner", "admin"]);

function WebSocketStatusPill({ status }: { status: "offline" | "connecting" | "connected" }) {
  const isConnected = status === "connected";
  const isConnecting = status === "connecting";

  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] font-medium uppercase tracking-[0.18em]"
      style={{
        borderColor: isConnected
          ? "color-mix(in srgb, var(--success) 42%, var(--border))"
          : isConnecting
            ? "color-mix(in srgb, var(--warning) 42%, var(--border))"
            : "var(--border-light)",
        background: isConnected
          ? "var(--success-bg)"
          : isConnecting
            ? "var(--warning-bg)"
            : "color-mix(in srgb, var(--bg-input) 82%, transparent)",
        color: isConnected ? "var(--success)" : isConnecting ? "var(--warning)" : "var(--text-muted)",
      }}
      title="WebSocket sync-events status"
    >
      <span
        className="h-2 w-2 rounded-full"
        style={{
          background: isConnected ? "var(--success)" : isConnecting ? "var(--warning)" : "var(--text-dimmed)",
          boxShadow: isConnected ? "0 0 12px color-mix(in srgb, var(--success) 55%, transparent)" : "none",
        }}
      />
      {status}
    </span>
  );
}

function getPageMeta(pathname: string) {
  if (pathname === "/") {
    return {
      title: "Operations cockpit",
      description: "Track live infrastructure docs, sync health, and the latest project activity.",
    };
  }

  const found = NAV.find((item) => item.to === pathname);
  if (found) {
    return {
      title: found.label,
      description: `Review ${found.label.toLowerCase()} in the SyncDoc operator workspace.`,
    };
  }

  return {
    title: "SyncDoc",
    description: "Infrastructure-aware living documentation for teams that ship from code.",
  };
}

export default function Layout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    const stored = window.localStorage.getItem("syncdoc_sidebar_collapsed");
    if (stored === "true" || stored === "false") return stored === "true";
    return window.innerWidth < 1200;
  });
  const [mobileOpen, setMobileOpen] = useState(false);
  const [appVersion, setAppVersion] = useState("dev");
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(getProjectId());
  const showLabels = !sidebarCollapsed || mobileOpen;
  const wsStatus = useSyncEvents(useCallback(() => {}, []));

  useEffect(() => {
    fetch("/api/version")
      .then((r) => r.json())
      .then((d) => setAppVersion(d.version))
      .catch(() => {});
  }, []);

  useEffect(() => {
    getProjects()
      .then((items) => {
        setProjects(items);
        if (items.length === 0) {
          setCurrentProjectId(null);
          setProjectId("");
          return;
        }
        const hasCurrent = currentProjectId
          ? items.some((project) => project.id === currentProjectId)
          : false;
        if (!hasCurrent) {
          setCurrentProjectId(items[0].id);
          setProjectId(items[0].id);
          window.location.reload();
        }
      })
      .catch(() => {});
  }, []);

  const isViewer = user?.role === "viewer";
  const navItems = NAV.filter((item) => {
    if (item.to === "/owner-explorer") return user?.role === "owner";
    if (item.to === "/admin") return ADMIN_ROLES.has(user?.role ?? "");
    if (isViewer && (item.to === "/audit" || item.to === "/organization")) return false;
    return true;
  });

  const pageMeta = getPageMeta(location.pathname);

  return (
    <div className="app-shell">
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className="flex min-h-screen gap-4 px-3 py-3 sm:px-4 lg:gap-5 lg:px-5 lg:py-5">
        <aside
          className={`app-panel fixed inset-y-3 left-3 z-50 flex shrink-0 flex-col overflow-hidden rounded-[28px] border transition-transform duration-300 lg:static lg:inset-auto lg:translate-x-0 ${
            mobileOpen ? "translate-x-0" : "-translate-x-[110%]"
          } ${sidebarCollapsed ? "w-[92px]" : "w-[308px]"}`}
          style={{ background: "var(--sidebar-bg)" }}
        >
          <div className="brand-ribbon h-[2px] w-full" />
          <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-4">
            <div className="flex min-w-0 items-center gap-3">
              <img
                src="/branding/syncdoc-logo.svg"
                alt="SyncDoc logo"
                className="h-11 w-11 shrink-0 rounded-2xl border border-[var(--border-light)] bg-[var(--bg-elevated)] p-2"
              />
              {showLabels && (
                <div className="min-w-0">
                  <img
                    src="/branding/syncdoc-wordmark.svg"
                    alt="SyncDoc"
                    className="h-7 max-w-[142px] object-contain"
                  />
                  <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">
                    Living infrastructure docs
                  </p>
                </div>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-[var(--text-muted)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)] lg:hidden"
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation"
              >
                <X className="h-4 w-4" />
              </button>
              <button
                type="button"
                className="hidden h-9 w-9 items-center justify-center rounded-xl text-[var(--text-muted)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)] lg:inline-flex"
                onClick={() =>
                  setSidebarCollapsed((prev) => {
                    const next = !prev;
                    window.localStorage.setItem("syncdoc_sidebar_collapsed", String(next));
                    return next;
                  })
                }
                aria-label={sidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
              >
                {sidebarCollapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {showLabels && projects.length > 0 && (
            <div className="border-b border-[var(--border)] px-4 py-4">
              <div className="app-kicker mb-2 text-[11px] text-[var(--text-muted)]">Project</div>
              <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-input)]/90 p-2">
                <select
                  value={currentProjectId ?? ""}
                  onChange={(e) => {
                    const next = e.target.value;
                    setCurrentProjectId(next);
                    setProjectId(next);
                    window.location.reload();
                  }}
                  className="w-full rounded-xl bg-transparent px-2 py-2 text-sm text-[var(--text-white)] focus:outline-none"
                >
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          <nav className="flex-1 overflow-y-auto px-3 py-4">
            <div className="app-kicker px-3 pb-3 text-[11px] text-[var(--text-muted)]">Workspace</div>
            <div className="space-y-1.5">
              {navItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    `group flex items-center gap-3 rounded-2xl border px-3 py-3 text-sm transition-all ${
                      isActive
                        ? "border-[var(--border-bright)] bg-[var(--accent-bg)] text-[var(--text-white)] shadow-[inset_0_1px_0_rgba(255,255,255,0.02)]"
                        : "border-transparent text-[var(--text-secondary)] hover:border-[var(--border)] hover:bg-[var(--hover-bg)] hover:text-[var(--text-white)]"
                    } ${sidebarCollapsed ? "lg:justify-center lg:px-0" : ""}`
                  }
                  title={label}
                >
                  <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--bg-input)]/90">
                    <Icon className="h-4 w-4" />
                  </span>
                  {showLabels && (
                    <span className="min-w-0 flex-1 truncate">
                      {label}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          </nav>

          <div className="border-t border-[var(--border)] p-3">
            {user && (
              <div className={`rounded-2xl border border-[var(--border)] bg-[var(--bg-input)]/80 p-3 ${sidebarCollapsed ? "lg:px-2 lg:py-3" : ""}`}>
                <div className={`flex items-center gap-3 ${sidebarCollapsed ? "lg:justify-center" : ""}`}>
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt={user.login} className="h-10 w-10 rounded-full border border-[var(--border-light)]" />
                  ) : (
                    <div className="h-10 w-10 rounded-full border border-[var(--border-light)] bg-[var(--accent-bg)]" />
                  )}
                  {showLabels && (
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-[var(--text-white)]">{user.login}</div>
                      <div className="app-kicker text-[10px] text-[var(--text-muted)]">{user.role}</div>
                    </div>
                  )}
                  <button
                    onClick={logout}
                    title="Logout"
                    className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-[var(--text-muted)] transition-colors hover:bg-[var(--danger-bg)] hover:text-[var(--danger)]"
                  >
                    <LogOut className="h-4 w-4" />
                  </button>
                </div>

                {showLabels && (
                  <>
                    <div className="mt-3 flex items-center justify-between gap-3">
                      <div>
                        <div className="app-kicker text-[10px] text-[var(--text-muted)]">Runtime</div>
                        <div className="mt-1 text-sm text-[var(--text-secondary)]">v{appVersion}</div>
                      </div>
                      <WebSocketStatusPill status={wsStatus} />
                    </div>
                    <div className="mt-3 flex items-center justify-between gap-2">
                      <NavLink
                        to="/settings"
                        className={({ isActive }) =>
                          `inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium transition-colors ${
                            isActive
                              ? "border-[var(--border-bright)] bg-[var(--accent-bg)] text-[var(--text-white)]"
                              : "border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)]"
                          }`
                        }
                      >
                        <Settings className="h-3.5 w-3.5" />
                        Preferences
                      </NavLink>
                      <ThemeSwitcher />
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          <div
            className="app-panel sticky top-3 z-30 rounded-[28px] border px-4 py-4 sm:px-5"
            style={{ background: "var(--topbar-bg)" }}
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-start gap-3">
                <button
                  type="button"
                  className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-input)]/90 text-[var(--text-secondary)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-primary)] lg:hidden"
                  onClick={() => setMobileOpen(true)}
                  aria-label="Open navigation"
                >
                  <Menu className="h-5 w-5" />
                </button>
                <div>
                  <div className="app-kicker text-[11px] text-[var(--text-muted)]">Operator workspace</div>
                  <h1 className="app-section-title mt-1 text-3xl text-[var(--text-white)]">{pageMeta.title}</h1>
                  <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">{pageMeta.description}</p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="rounded-full border border-[var(--border)] bg-[var(--bg-input)]/80 px-3 py-2 text-xs text-[var(--text-secondary)]">
                  Current route
                  <span className="ml-2 font-medium text-[var(--text-white)]">{location.pathname}</span>
                </div>
                <a
                  href="https://syncdoc.dev"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--bg-input)]/80 px-3 py-2 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--hover-bg)] hover:text-[var(--text-white)]"
                >
                  Marketing site
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </a>
              </div>
            </div>
          </div>

          <div className="min-w-0 flex-1 px-0 py-4 sm:py-5">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
