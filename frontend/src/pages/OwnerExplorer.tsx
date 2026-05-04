import { useEffect, useMemo, useState } from "react";
import { Database, Search, AlertCircle, RefreshCcw, Eye } from "lucide-react";
import {
  getOwnerExplorerItem,
  getOwnerExplorerItems,
  getOwnerExplorerResources,
} from "../api/client";
import type {
  OwnerExplorerDetailResponse,
  OwnerExplorerListResponse,
  OwnerExplorerResource,
} from "../types";
import { useAuth } from "../context/AuthContext";

const PAGE_SIZE = 20;

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}T/.test(text)) {
    const parsed = new Date(text);
    if (!Number.isNaN(parsed.getTime())) return parsed.toLocaleString();
  }
  return text;
}

export default function OwnerExplorerPage() {
  const { user } = useAuth();
  const [resources, setResources] = useState<OwnerExplorerResource[]>([]);
  const [selectedResource, setSelectedResource] = useState("");
  const [listData, setListData] = useState<OwnerExplorerListResponse | null>(null);
  const [detailData, setDetailData] = useState<OwnerExplorerDetailResponse | null>(null);
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");

  const isOwner = user?.role === "owner";

  useEffect(() => {
    if (!isOwner) return;
    setLoading(true);
    setError("");
    getOwnerExplorerResources()
      .then((items) => {
        setResources(items);
        setSelectedResource((current) => current || items[0]?.key || "");
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load explorer resources");
      })
      .finally(() => setLoading(false));
  }, [isOwner]);

  useEffect(() => {
    if (!isOwner || !selectedResource) return;
    setLoading(true);
    setError("");
    setDetailData(null);
    getOwnerExplorerItems(selectedResource, {
      limit: PAGE_SIZE,
      offset,
      q: query.trim() || undefined,
    })
      .then((data) => setListData(data))
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load explorer data");
      })
      .finally(() => setLoading(false));
  }, [isOwner, selectedResource, offset, query]);

  const currentLabel = useMemo(() => {
    return resources.find((resource) => resource.key === selectedResource)?.label ?? "Resource";
  }, [resources, selectedResource]);

  const handleInspect = async (itemId: string) => {
    setDetailLoading(true);
    setError("");
    try {
      const data = await getOwnerExplorerItem(selectedResource, itemId);
      setDetailData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load record details");
    } finally {
      setDetailLoading(false);
    }
  };

  if (!isOwner) {
    return (
      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6 text-sm text-[var(--text-secondary)]">
        This page is available to organization owners only.
      </div>
    );
  }

  const canGoBack = offset > 0;
  const canGoForward = Boolean(listData && offset + PAGE_SIZE < listData.total);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-[var(--text-white)]">
            <Database className="h-6 w-6" />
            Owner Explorer
          </h1>
          <p className="mt-1 text-[var(--text-secondary)]">
            Read-only operational visibility into key SyncDoc data.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setOffset(0);
            setDetailData(null);
            setLoading(true);
            getOwnerExplorerItems(selectedResource, {
              limit: PAGE_SIZE,
              offset: 0,
              q: query.trim() || undefined,
            })
              .then((data) => setListData(data))
              .catch((err) => {
                setError(err instanceof Error ? err.message : "Failed to refresh explorer data");
              })
              .finally(() => setLoading(false));
          }}
          className="inline-flex items-center gap-2 rounded-lg border border-[var(--border-light)] bg-[var(--bg-card)] px-4 py-2 text-sm text-[var(--text-primary)] transition-colors hover:bg-[var(--hover-bg)]"
        >
          <RefreshCcw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="grid gap-6 2xl:grid-cols-[minmax(0,3fr)_minmax(360px,1fr)]">
        <section className="space-y-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <div className="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-[var(--text-secondary)]">
                Resource
              </label>
              <select
                value={selectedResource}
                onChange={(e) => {
                  setSelectedResource(e.target.value);
                  setOffset(0);
                  setDetailData(null);
                }}
                className="w-full rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent-strong)] focus:outline-none"
              >
                {resources.map((resource) => (
                  <option key={resource.key} value={resource.key}>
                    {resource.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-[var(--text-secondary)]">
                Search
              </label>
              <div className="flex items-center gap-2 rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3">
                <Search className="h-4 w-4 text-[var(--text-muted)]" />
                <input
                  value={query}
                  onChange={(e) => {
                    setOffset(0);
                    setQuery(e.target.value);
                  }}
                  placeholder={`Search ${currentLabel.toLowerCase()}`}
                  className="w-full bg-transparent py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
                />
              </div>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
            <table className="min-w-full divide-y divide-[var(--border)] text-sm">
              <thead className="bg-[var(--bg-secondary)]/60">
                <tr>
                  {listData?.columns.map((column) => (
                    <th
                      key={column}
                      className="whitespace-nowrap px-3 py-2 text-left font-medium uppercase tracking-wide text-[10px] text-[var(--text-muted)]"
                    >
                      {column.replace(/_/g, " ")}
                    </th>
                  ))}
                  <th className="px-3 py-2 text-right font-medium uppercase tracking-wide text-[10px] text-[var(--text-muted)]">
                    Inspect
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {loading ? (
                  <tr>
                    <td
                      colSpan={(listData?.columns.length ?? 0) + 1}
                      className="px-4 py-10 text-center text-[var(--text-secondary)]"
                    >
                      Loading {currentLabel.toLowerCase()}...
                    </td>
                  </tr>
                ) : listData?.items.length ? (
                  listData.items.map((item, index) => {
                    const itemId = String(item.id ?? index);
                    return (
                      <tr key={itemId} className="bg-[var(--bg-card)]">
                        {listData.columns.map((column) => (
                          <td
                            key={`${itemId}-${column}`}
                            className="max-w-[320px] whitespace-nowrap px-3 py-2 align-top text-[var(--text-primary)]"
                          >
                            <span className="block truncate" title={formatValue(item[column])}>
                              {formatValue(item[column])}
                            </span>
                          </td>
                        ))}
                        <td className="px-3 py-2 text-right">
                          <button
                            type="button"
                            onClick={() => handleInspect(itemId)}
                            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-[var(--accent)] transition-colors hover:bg-[var(--accent-bg)]"
                          >
                            <Eye className="h-3.5 w-3.5" />
                            View
                          </button>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td
                      colSpan={(listData?.columns.length ?? 0) + 1}
                      className="px-4 py-10 text-center text-[var(--text-secondary)]"
                    >
                      No records found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-sm text-[var(--text-secondary)]">
            <span>
              {listData
                ? `${Math.min(offset + 1, listData.total)}-${Math.min(offset + PAGE_SIZE, listData.total)} of ${listData.total}`
                : "0 results"}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={!canGoBack}
                onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
                className="rounded-lg border border-[var(--border-light)] px-3 py-1.5 transition-colors hover:bg-[var(--hover-bg)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={!canGoForward}
                onClick={() => setOffset((current) => current + PAGE_SIZE)}
                className="rounded-lg border border-[var(--border-light)] px-3 py-1.5 transition-colors hover:bg-[var(--hover-bg)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </section>

        <aside className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
          <h2 className="text-lg font-semibold text-[var(--text-white)]">Record Detail</h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Inspect a sanitized record from the selected resource.
          </p>
          <div className="mt-4">
            {detailLoading ? (
              <div className="text-sm text-[var(--text-secondary)]">Loading record...</div>
            ) : detailData ? (
              <dl className="space-y-3">
                {Object.entries(detailData.item).map(([key, value]) => (
                  <div key={key} className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)]/40 p-3">
                    <dt className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">
                      {key.replace(/_/g, " ")}
                    </dt>
                    <dd className="mt-1 whitespace-pre-wrap break-words text-sm text-[var(--text-primary)]">
                      {formatValue(value)}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <div className="text-sm text-[var(--text-secondary)]">
                Select a row to inspect its details.
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
