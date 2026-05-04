import { useEffect, useState, useCallback } from "react";
import {
  Settings as SettingsIcon,
  RotateCcw,
  Save,
  Eye,
  EyeOff,
  Check,
  AlertCircle,
  Github,
  Key,
  Plus,
  Trash2,
  Copy,
  CheckCircle,
} from "lucide-react";
import { getSettings, updateSettings, createApiKey, listApiKeys, revokeApiKey, type ApiKeyInfo } from "../api/client";
import type { AppSettings } from "../types";
import { THEMES, useTheme } from "../context/ThemeContext";
import UpgradeBadge from "../components/UpgradeBadge";
import { useAuth } from "../context/AuthContext";

const PROVIDER_DEFAULTS: Record<string, { model: string; endpoint: string }> = {
  openai: { model: "gpt-4o", endpoint: "https://api.openai.com/v1" },
  anthropic: { model: "claude-sonnet-4-20250514", endpoint: "https://api.anthropic.com" },
};

function isMasked(val: string | null): boolean {
  return !!val && val.startsWith("••••");
}

export default function Settings() {
  const { theme, setTheme, isThemeLocked } = useTheme();
  const { user } = useAuth();
  const canManage = user?.role === "owner" || user?.role === "admin";

  const [form, setForm] = useState<AppSettings>({
    llm_provider: "openai",
    llm_model: "gpt-4o",
    llm_endpoint_url: "https://api.openai.com/v1",
    llm_api_key: null,
    notification_type: "slack",
    slack_webhook_url: null,
    github_token: null,
  });
  const [dirty, setDirty] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  // API Keys state
  const [apiKeys, setApiKeys] = useState<ApiKeyInfo[]>([]);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [creatingKey, setCreatingKey] = useState(false);

  const loadApiKeys = useCallback(async () => {
    try {
      const keys = await listApiKeys();
      setApiKeys(keys);
    } catch {
      // API keys endpoint may not exist yet
    }
  }, []);

  const load = useCallback(async () => {
    try {
      const data = await getSettings();
      setForm(data);
      setDirty(new Set());
    } catch {
      // Settings endpoint may not exist yet (migration pending)
    }
  }, []);

  useEffect(() => {
    load();
    loadApiKeys();
  }, [load, loadApiKeys]);

  const updateField = (key: keyof AppSettings, value: string | null) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setDirty((prev) => new Set(prev).add(key));
    setSaved(false);
  };

  const handleProviderChange = (provider: string) => {
    const defaults = PROVIDER_DEFAULTS[provider];
    setForm((prev) => ({
      ...prev,
      llm_provider: provider,
      llm_model: defaults?.model ?? prev.llm_model,
      llm_endpoint_url: defaults?.endpoint ?? prev.llm_endpoint_url,
    }));
    setDirty((prev) => {
      const next = new Set(prev);
      next.add("llm_provider");
      next.add("llm_model");
      next.add("llm_endpoint_url");
      return next;
    });
    setSaved(false);
  };

  const handleResetAI = () => {
    const defaults = PROVIDER_DEFAULTS[form.llm_provider] ?? PROVIDER_DEFAULTS.openai;
    setForm((prev) => ({
      ...prev,
      llm_model: defaults.model,
      llm_endpoint_url: defaults.endpoint,
    }));
    setDirty((prev) => {
      const next = new Set(prev);
      next.add("llm_model");
      next.add("llm_endpoint_url");
      return next;
    });
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      // Only send dirty fields, skip masked values
      const payload: Record<string, string | null> = {};
      for (const key of dirty) {
        const val = form[key as keyof AppSettings];
        if (val !== null && isMasked(val)) continue;
        payload[key] = val;
      }
      if (Object.keys(payload).length === 0) {
        setSaving(false);
        return;
      }
      const updated = await updateSettings(payload);
      setForm(updated);
      setDirty(new Set());
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const toggleShowKey = (key: string) =>
    setShowKeys((prev) => ({ ...prev, [key]: !prev[key] }));

  const inputCls =
    "w-full rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-strong)] transition-colors";
  const labelCls = "block text-sm font-medium text-[var(--text-secondary)] mb-1.5";
  const cardCls =
    "rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6 space-y-5";
  const sectionTitle = "text-lg font-semibold text-[var(--text-white)] mb-1";

  return (
    <>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-white)] flex items-center gap-2">
            <SettingsIcon className="w-6 h-6" />
            Settings
          </h1>
          <p className="text-[var(--text-secondary)] mt-1">
            Configure AI, notifications, and appearance
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={!canManage || saving || dirty.size === 0}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-strong)] hover:bg-[var(--accent-hover)] text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : saved ? (
            <Check className="w-4 h-4" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {saving ? "Saving..." : saved ? "Saved" : "Save Changes"}
        </button>
      </div>

      {!canManage && (
        <div className="flex items-center gap-2 p-3 mb-6 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          You have read-only access. Only owners and admins can update settings.
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 mb-6 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <fieldset disabled={!canManage} className="space-y-6">
        {/* AI Configuration */}
        <div className={cardCls}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className={sectionTitle}>AI Configuration</h2>
              <p className="text-sm text-[var(--text-muted)]">
                Configure the LLM provider for documentation generation
              </p>
            </div>
            <button
              onClick={handleResetAI}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-light)] text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--hover-bg)] transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset to Defaults
            </button>
          </div>

          <div className="grid grid-cols-2 gap-5">
            <div>
              <label className={labelCls}>Provider</label>
              <select
                value={form.llm_provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className={inputCls}
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Model</label>
              <input
                type="text"
                value={form.llm_model}
                onChange={(e) => updateField("llm_model", e.target.value)}
                placeholder={PROVIDER_DEFAULTS[form.llm_provider]?.model}
                className={inputCls}
              />
            </div>
          </div>

          <div>
            <label className={labelCls}>Endpoint URL</label>
            <input
              type="text"
              value={form.llm_endpoint_url}
              onChange={(e) => updateField("llm_endpoint_url", e.target.value)}
              placeholder={PROVIDER_DEFAULTS[form.llm_provider]?.endpoint}
              className={inputCls}
            />
            <p className="mt-1.5 text-xs text-[var(--text-muted)]">
              For local models with{" "}
              <span className="font-mono text-[var(--text-secondary)]">
                LM Studio
              </span>
              , use{" "}
              <code className="px-1 py-0.5 rounded bg-[var(--bg-input)] text-[var(--accent)] text-[11px]">
                http://host.docker.internal:1234/v1
              </code>{" "}
              or another compatible provider endpoint.
            </p>
          </div>

          <div>
            <label className={labelCls}>LLM API Key</label>
            <div className="relative">
              <input
                type={showKeys.api_key ? "text" : "password"}
                value={form.llm_api_key ?? ""}
                onChange={(e) => updateField("llm_api_key", e.target.value || null)}
                placeholder="Enter API key..."
                className={`${inputCls} pr-10`}
              />
              <button
                type="button"
                onClick={() => toggleShowKey("api_key")}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              >
                {showKeys.api_key ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Theme */}
        <div className={cardCls}>
          <div>
            <h2 className={sectionTitle}>Theme</h2>
            <p className="text-sm text-[var(--text-muted)]">
              Choose your preferred color scheme
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {THEMES.map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  if (!isThemeLocked(t.id)) setTheme(t.id);
                }}
                className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${
                  theme === t.id
                    ? "border-[var(--accent-strong)] bg-[var(--accent-strong)]/10"
                    : "border-[var(--border-light)] hover:bg-[var(--hover-bg)]"
                } ${isThemeLocked(t.id) ? "opacity-70" : ""}`}
                disabled={isThemeLocked(t.id)}
              >
                <span
                  className="w-5 h-5 rounded-full shrink-0 ring-2 ring-offset-2 ring-offset-[var(--bg-card)]"
                  style={{
                    backgroundColor: t.swatch,
                    "--tw-ring-color": theme === t.id ? t.swatch : "transparent",
                  } as React.CSSProperties}
                />
                <span
                  className={`text-sm ${
                    theme === t.id
                      ? "text-[var(--text-white)] font-medium"
                      : "text-[var(--text-secondary)]"
                  }`}
                >
                  {t.label}
                </span>
                {isThemeLocked(t.id) && <UpgradeBadge label="Pro" />}
                {theme === t.id && (
                  <Check className="w-4 h-4 text-[var(--accent)] ml-auto" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Notifications */}
        <div className={cardCls}>
          <div>
            <h2 className={sectionTitle}>Notifications</h2>
            <p className="text-sm text-[var(--text-muted)]">
              Configure alerts for drift events and sync failures
            </p>
          </div>

          <div className="grid grid-cols-2 gap-5">
            <div>
              <label className={labelCls}>Notification Type</label>
              <select
                value={form.notification_type ?? "slack"}
                onChange={(e) =>
                  updateField("notification_type", e.target.value)
                }
                className={inputCls}
              >
                <option value="slack">Slack</option>
                <option value="none">Disabled</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Webhook URL</label>
              <div className="relative">
                <input
                  type={showKeys.webhook ? "text" : "password"}
                  value={form.slack_webhook_url ?? ""}
                  onChange={(e) =>
                    updateField("slack_webhook_url", e.target.value || null)
                  }
                  placeholder="https://hooks.slack.com/services/..."
                  disabled={form.notification_type === "none"}
                  className={`${inputCls} pr-10 disabled:opacity-50`}
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey("webhook")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                >
                  {showKeys.webhook ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* GitHub Authentication */}
        <div className={cardCls}>
          <div className="flex items-center gap-3 mb-5">
            <Github className="w-5 h-5 text-[var(--text-muted)]" />
            <div>
              <h2 className={sectionTitle}>GitHub Authentication</h2>
              <p className="text-sm text-[var(--text-muted)]">
                Global GitHub Personal Access Token for private repository access
              </p>
            </div>
          </div>
          <div>
            <label className={labelCls}>Personal Access Token</label>
            <div className="relative">
              <input
                type={showKeys.github_token ? "text" : "password"}
                value={form.github_token ?? ""}
                onChange={(e) => updateField("github_token", e.target.value || null)}
                placeholder="ghp_..."
                className={`${inputCls} pr-10`}
              />
              <button
                type="button"
                onClick={() => toggleShowKey("github_token")}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              >
                {showKeys.github_token ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="mt-1.5 text-xs text-[var(--text-muted)]">
              Used as a fallback for all git sources without per-source credentials. Needs <code className="px-1 py-0.5 rounded bg-[var(--bg-input)] text-[var(--accent)] text-[11px]">repo</code> scope.
            </p>
          </div>
        </div>

        {/* API Keys */}
        <div className={cardCls}>
          <div className="flex items-center gap-3 mb-5">
            <Key className="w-5 h-5 text-[var(--text-muted)]" />
            <div>
              <h2 className={sectionTitle}>API Keys</h2>
              <p className="text-sm text-[var(--text-muted)]">
                Create API keys for programmatic access
              </p>
            </div>
          </div>

          {/* Create new key */}
          <div className="flex gap-3 mb-6">
            <input
              type="text"
              placeholder="Key name (e.g., my-cli)"
              className={inputCls}
              id="newApiKeyName"
            />
            <button
              onClick={async () => {
                const name = (document.getElementById("newApiKeyName") as HTMLInputElement).value;
                if (!name) return;
                setCreatingKey(true);
                try {
                  const created = await createApiKey(name);
                  setNewApiKey(created.key);
                  setApiKeys(prev => [...prev, { id: created.id, name: created.name, prefix: created.prefix, created_at: created.created_at, expires_at: created.expires_at, last_used_at: null }]);
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Failed to create key");
                } finally {
                  setCreatingKey(false);
                }
              }}
              disabled={creatingKey}
              className="flex items-center gap-2 px-4 py-2 bg-[var(--accent-icon)] hover:opacity-90 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              <Plus className="w-4 h-4" /> Generate Key
            </button>
          </div>

          {/* Show newly created key */}
          {newApiKey && (
            <div className="mb-6 p-4 rounded-lg bg-emerald-950/20 border border-emerald-900/50">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-medium text-emerald-400">Key created! Copy it now - you won't see it again.</span>
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-2 rounded bg-slate-900 text-emerald-400 text-xs font-mono break-all">
                  {newApiKey}
                </code>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(newApiKey);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="p-2 rounded hover:bg-slate-800 transition-colors"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                </button>
                <button
                  onClick={() => setNewApiKey(null)}
                  className="p-2 rounded hover:bg-slate-800 transition-colors"
                >
                  <span className="text-xs text-slate-400">Done</span>
                </button>
              </div>
            </div>
          )}

          {/* List existing keys */}
          {apiKeys.length > 0 ? (
            <div className="space-y-2">
              {apiKeys.map(key => (
                <div key={key.id} className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-input)] border border-[var(--border)]">
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)]">{key.name}</p>
                    <p className="text-xs text-[var(--text-muted)] font-mono">{key.prefix}••••••••</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {key.expires_at && (
                      <span className="text-xs text-[var(--text-muted)]">
                        Expires: {new Date(key.expires_at).toLocaleDateString()}
                      </span>
                    )}
                    <button
                      onClick={async () => {
                        if (!confirm("Are you sure you want to revoke this key?")) return;
                        try {
                          await revokeApiKey(key.id);
                          setApiKeys(prev => prev.filter(k => k.id !== key.id));
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Failed to revoke key");
                        }
                      }}
                      className="p-2 rounded hover:bg-red-900/20 text-red-400 transition-colors"
                      title="Revoke key"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-muted)]">No API keys created yet.</p>
          )}

          {/* How to use */}
          <div className="mt-6 p-4 rounded-lg bg-[var(--bg-input)] border border-[var(--border)]">
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-2">How to use</h3>
            <p className="text-xs text-[var(--text-muted)] mb-3">
              Use the API key in the <code className="px-1 py-0.5 rounded bg-slate-800 text-amber-400">Authorization</code> header:
            </p>
            <pre className="text-xs text-slate-300 font-mono p-3 rounded bg-slate-900 overflow-x-auto">
{`# Export your key
export API_KEY="syncdoc_abc123..."

# Create a new key
curl -X POST https://api.syncdoc.dev/api/api-keys \\
  -H "Authorization: Bearer <your_jwt_token>" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "my-tool"}'

# Use the key
curl https://api.syncdoc.dev/api/sources/ \\
  -H "Authorization: ApiKey $API_KEY"`}
            </pre>
          </div>
        </div>
      </fieldset>
    </>
  );
}
