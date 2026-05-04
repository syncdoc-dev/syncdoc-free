import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Search as SearchIcon, Server, FileText, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { getSettings, searchAll } from "../api/client";
import type { AppSettings, SearchResults } from "../types";
import { useAuth } from "../context/AuthContext";
import UpgradeBadge from "../components/UpgradeBadge";

export default function Search() {
  const { hasFeature } = useAuth();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults(null);
      return;
    }
    setLoading(true);
    try {
      const data = await searchAll(q);
      setResults(data);
    } catch {
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(query), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, doSearch]);

  useEffect(() => {
    getSettings()
      .then((settings) => setAppSettings(settings))
      .catch((err) =>
        setSettingsError(err instanceof Error ? err.message : "Failed to load settings")
      );
  }, []);

  const totalResults = results
    ? results.nodes.length + results.pages.length
    : 0;
  const semanticLicensed = hasFeature("semantic_search");

  return (
    <>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--text-white)]">Search</h1>
        <p className="text-[var(--text-secondary)] mt-1">
          Find infrastructure resources and documentation
        </p>
      </div>

      {/* Search mode availability */}
      {(() => {
        const hasLlmKey = appSettings && !!appSettings.llm_api_key;
        const enabled = !!hasLlmKey && semanticLicensed;
        return (
          <div
            className={`mb-6 rounded-xl border p-4 ${
              enabled
                ? "border-emerald-500/30 bg-emerald-500/10"
                : "border-amber-500/30 bg-amber-500/10"
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              {enabled ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 text-amber-400" />
              )}
              <h3 className="text-sm font-semibold text-[var(--text-white)]">
                Semantic Search
              </h3>
              {!enabled && !semanticLicensed && <UpgradeBadge label="Pro" />}
            </div>
            <p
              className={`text-xs ${
                enabled ? "text-emerald-200/90" : "text-amber-200/90"
              }`}
            >
              {enabled
                ? "Embedding-based semantic search is enabled."
                : semanticLicensed
                  ? "Keyword search only until an LLM key is configured."
                  : "Keyword search only. Upgrade your license to enable semantic search."}
            </p>
          </div>
        );
      })()}

      {settingsError && (
        <div className="mb-6 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs text-amber-200/90">
          Unable to load LLM configuration. Search mode indicator may be inaccurate.
        </div>
      )}

      {/* Search input */}
      <div className="relative mb-6">
        <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)]" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search nodes, resources, pages..."
          autoFocus
          className="w-full pl-12 pr-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/60 transition-all"
        />
        {loading && (
          <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-violet-400 animate-spin" />
        )}
      </div>

      {/* Results */}
      {results && query.length >= 2 && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <p className="text-sm text-[var(--text-secondary)]">
              {totalResults} result{totalResults !== 1 ? "s" : ""} for &ldquo;
              {results.query}&rdquo;
            </p>
            {results.search_mode === "semantic" && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-violet-500/20 text-violet-300 border border-violet-500/30">
                <span className="w-1.5 h-1.5 bg-violet-400 rounded-full"></span>
                semantic
              </span>
            )}
          </div>

          {/* Node results */}
          {results.nodes.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-3">
                Infrastructure Resources ({results.nodes.length})
              </h2>
              <div className="space-y-2">
                {results.nodes.map((node) => (
                  <Link
                    key={node.id}
                    to="/graph"
                    className="flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--hover-bg)] transition-colors"
                  >
                    <Server className="w-4 h-4 text-violet-400 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                        {node.name}
                      </p>
                      <p className="text-xs text-[var(--text-muted)]">
                        {node.kind}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Page results */}
          {results.pages.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-3">
                Documentation ({results.pages.length})
              </h2>
              <div className="space-y-2">
                {results.pages.map((page) => (
                  <Link
                    key={page.id}
                    to={`/pages/${page.id}`}
                    className="flex items-start gap-3 p-3 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--hover-bg)] transition-colors"
                  >
                    <FileText className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-[var(--text-primary)]">
                        {page.title}
                      </p>
                      {page.snippet && (
                        <p className="text-xs text-[var(--text-muted)] mt-1 line-clamp-2">
                          {page.snippet}
                        </p>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {totalResults === 0 && (
            <div className="flex flex-col items-center justify-center h-[200px] rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-muted)]">
              <SearchIcon className="w-8 h-8 mb-2" />
              <p>No results found</p>
              <p className="text-sm mt-1">Try a different search term</p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!results && query.length < 2 && (
        <div className="flex flex-col items-center justify-center h-[300px] rounded-xl border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-muted)]">
          <SearchIcon className="w-10 h-10 mb-3" />
          <p>Start typing to search</p>
          <p className="text-sm mt-1">
            Search across infrastructure nodes and documentation pages
          </p>
        </div>
      )}
    </>
  );
}
