import type {
  Source,
  Page,
  GraphData,
  DriftEvent,
  DriftStats,
  SearchResults,
  AppSettings,
  AnalyticsData,
  PageWithWorkflow,
  PageVersion,
  WorkflowAuditLog,
  Project,
  Organization,
  OrgMember,
  GraphNote,
  ManualGraphEdge,
  LicenseRecord,
  Entitlements,
  OwnerExplorerDetailResponse,
  OwnerExplorerListResponse,
  OwnerExplorerResource,
  SourceInspection,
} from "../types";

const BASE = "/api";
const PROJECT_KEY = "syncdoc_project_id";

export function getProjectId(): string | null {
  const value = localStorage.getItem(PROJECT_KEY);
  if (!value) return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function setProjectId(projectId: string): void {
  if (!projectId) {
    localStorage.removeItem(PROJECT_KEY);
    return;
  }
  localStorage.setItem(PROJECT_KEY, projectId);
}

export function getApiBase(): string {
  const apiUrl = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  return apiUrl.endsWith("/api") ? apiUrl : `${apiUrl}/api`;
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("syncdoc_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function isHtmlResponse(res: Response): boolean {
  const contentType = res.headers.get("content-type") || "";
  return contentType.includes("text/html");
}

export async function apiFetch(path: string, options?: RequestInit): Promise<Response> {
  const preferredBase = import.meta.env.VITE_API_URL ? getApiBase() : BASE;
  const projectId = getProjectId();
  const url = new URL(`${preferredBase}${path}`, window.location.origin);
  if (projectId && !url.searchParams.has("project_id")) {
    url.searchParams.set("project_id", projectId);
  }
  const res = await fetch(url.toString(), {
    headers: { "Content-Type": "application/json", ...authHeaders() },
    ...options,
  });
  if (isHtmlResponse(res) && preferredBase !== BASE) {
    const fallbackUrl = new URL(`${BASE}${path}`, window.location.origin);
    if (projectId && !fallbackUrl.searchParams.has("project_id")) {
      fallbackUrl.searchParams.set("project_id", projectId);
    }
    return fetch(fallbackUrl.toString(), {
      headers: { "Content-Type": "application/json", ...authHeaders() },
      ...options,
    });
  }
  return res;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await apiFetch(path, options);
  if (isHtmlResponse(res)) {
    throw new Error("API endpoint misconfigured (received HTML). Check /api routing.");
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Health
export const getHealth = () => request<{ status: string }>("/health");

// Sources
export const getSources = () => request<Source[]>("/sources/");
export const createSource = (data: { type: string; url: string }) => {
  const projectId = getProjectId();
  const payload = projectId ? { ...data, project_id: projectId } : data;
  return request<Source>("/sources/", { method: "POST", body: JSON.stringify(payload) });
};
export const inspectSource = (data: { type: string; url: string }) =>
  request<SourceInspection>("/sources/inspect", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const deleteSource = (id: string) =>
  request<void>(`/sources/${id}`, { method: "DELETE" });
export const syncSource = (id: string) =>
  request<{ status: string; task_id: string }>(`/sources/${id}/sync`, {
    method: "POST",
  });

// Pages
export const getPages = (sourceId?: string, includeWorkflow = false) => {
  const params = new URLSearchParams();
  if (sourceId) params.set("source_id", sourceId);
  if (includeWorkflow) params.set("include_workflow", "true");
  const qs = params.toString();
  return request<Page[]>(`/pages/${qs ? `?${qs}` : ""}`);
};
export const getPage = (id: string) => request<Page>(`/pages/${id}`);
export const updatePage = (id: string, content: string) =>
  request<Page>(`/pages/${id}`, {
    method: "PUT",
    body: JSON.stringify({ content_md: content }),
  });
export const regeneratePage = (id: string) =>
  request<Page>(`/pages/${id}/regenerate`, { method: "POST" });
export const deletePage = (id: string) =>
  request<void>(`/pages/${id}`, { method: "DELETE" });

// Drift
export const getDriftEvents = (sourceId?: string, resolved?: number) => {
  const params = new URLSearchParams();
  if (sourceId) params.set("source_id", sourceId);
  if (resolved !== undefined) params.set("resolved", String(resolved));
  const qs = params.toString();
  return request<DriftEvent[]>(`/drift/${qs ? `?${qs}` : ""}`);
};
export const getDriftStats = () => request<DriftStats>("/drift/stats");
export const resolveDriftEvent = (id: string, notes?: string) =>
  request<DriftEvent>(`/drift/${id}/resolve`, {
    method: "POST",
    body: JSON.stringify({ resolution_notes: notes || null }),
  });

// Search
export const searchAll = (q: string, limit = 20) =>
  request<SearchResults>(`/search/?q=${encodeURIComponent(q)}&limit=${limit}`);

// Settings
export const getSettings = () => request<AppSettings>("/settings/");
export const updateSettings = (data: Partial<AppSettings>) =>
  request<AppSettings>("/settings/", { method: "PUT", body: JSON.stringify(data) });

// User profile
export const updateMe = (data: { theme_id?: string | null }) =>
  request<Record<string, unknown>>("/auth/me", { method: "PATCH", body: JSON.stringify(data) });

export const forgotPassword = (loginOrEmail: string) =>
  request<{ detail: string }>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ login_or_email: loginOrEmail }),
  });

export const resetPassword = (token: string, password: string) =>
  request<{ detail: string }>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, password }),
  });

// Graph
export const getGraph = (sourceId?: string) =>
  request<GraphData>(`/graph/${sourceId ? `?source_id=${sourceId}` : ""}`);

// Graph notes
export const createGraphNote = (payload: {
  content: string;
  pos_x: number;
  pos_y: number;
  color?: string;
  from_node_id?: string | null;
  to_node_id?: string | null;
  source_id?: string | null;
}) => request<GraphNote>("/graph/notes", { method: "POST", body: JSON.stringify(payload) });

export const updateGraphNote = (id: string, payload: Partial<{
  content: string;
  pos_x: number;
  pos_y: number;
  color: string;
}>) => request<GraphNote>(`/graph/notes/${id}`, { method: "PATCH", body: JSON.stringify(payload) });

export const deleteGraphNote = (id: string) =>
  request<void>(`/graph/notes/${id}`, { method: "DELETE" });

// Manual edges
export const createManualEdge = (payload: {
  from_node_id: string;
  to_node_id: string;
  label?: string | null;
  color?: string | null;
}) => request<ManualGraphEdge>("/graph/edges", { method: "POST", body: JSON.stringify(payload) });

export const updateManualEdge = (id: string, payload: Partial<{ label: string | null; color: string }>) =>
  request<ManualGraphEdge>(`/graph/edges/${id}`, { method: "PATCH", body: JSON.stringify(payload) });

export const deleteManualEdge = (id: string) =>
  request<void>(`/graph/edges/${id}`, { method: "DELETE" });

// Credentials
export const createCredential = (sourceId: string, data: { credential_type: string; secret_value: string }) =>
  request<{ id: string; credential_type: string; created_at: string }>(`/sources/${sourceId}/credentials`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export const listCredentials = (sourceId: string) =>
  request<{ source_id: string; credentials: Array<{ id: string; credential_type: string; created_at: string }> }>(`/sources/${sourceId}/credentials`);

export const deleteCredential = (sourceId: string, credentialId: string) =>
  request<void>(`/sources/${sourceId}/credentials/${credentialId}`, { method: "DELETE" });

// Projects
export const getProjects = () => request<Project[]>("/projects/");
export const createProject = (name: string) =>
  request<Project>("/projects/", { method: "POST", body: JSON.stringify({ name }) });

// Organization
export const getOrganization = () => request<Organization>("/orgs/me");
export const updateOrganization = (name: string) =>
  request<Organization>("/orgs/me", { method: "PUT", body: JSON.stringify({ name }) });
export const getOrganizationMembers = () => request<OrgMember[]>("/orgs/members");
export const createOrganizationUser = (payload: { login: string; email?: string; name?: string; password: string; role: string; }) =>
  request<OrgMember>("/orgs/users", { method: "POST", body: JSON.stringify(payload) });
export const updateOrganizationMemberRole = (userId: number, role: string) =>
  request<OrgMember>(`/orgs/members/${userId}`, { method: "PATCH", body: JSON.stringify({ role }) });
export const deleteOrganizationUser = (userId: number) =>
  request<void>(`/orgs/users/${userId}`, { method: "DELETE" });

// License
export const getLicense = () => request<LicenseRecord>("/license");
export const installLicense = (licenseToken: string) =>
  request<LicenseRecord>("/license", {
    method: "PUT",
    body: JSON.stringify({ license_token: licenseToken }),
  });
export const deleteLicense = () =>
  request<void>("/license", { method: "DELETE" });
export const getEntitlements = () => request<Entitlements>("/license/entitlements");

// Sync runs
export const getSyncRuns = (sourceId: string) =>
  request<Array<{ id: string; status: string; started_at: string; completed_at: string | null; nodes_added: number; nodes_updated: number; error_message: string | null }>>(`/sources/${sourceId}/sync-runs`);

export type SyncRunWithSource = {
  id: string;
  source_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  nodes_added: number;
  nodes_updated: number;
  drift_count: number;
  error_message: string | null;
  source_name: string | null;
  source_type: string | null;
};

export const getAllSyncRuns = (limit = 50, sourceId?: string, status?: string) => {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (sourceId) params.set("source_id", sourceId);
  if (status) params.set("status", status);
  return request<SyncRunWithSource[]>(`/sources/sync-runs?${params.toString()}`);
};

// Owner explorer
export const getOwnerExplorerResources = () =>
  request<OwnerExplorerResource[]>("/owner-explorer/resources");

export const getOwnerExplorerItems = (
  resource: string,
  options?: { limit?: number; offset?: number; q?: string }
) => {
  const params = new URLSearchParams();
  if (options?.limit !== undefined) params.set("limit", String(options.limit));
  if (options?.offset !== undefined) params.set("offset", String(options.offset));
  if (options?.q) params.set("q", options.q);
  const qs = params.toString();
  return request<OwnerExplorerListResponse>(
    `/owner-explorer/${resource}${qs ? `?${qs}` : ""}`
  );
};

export const getOwnerExplorerItem = (resource: string, itemId: string) =>
  request<OwnerExplorerDetailResponse>(`/owner-explorer/${resource}/${encodeURIComponent(itemId)}`);

// API Keys
export type ApiKeyInfo = {
  id: number;
  name: string;
  prefix: string;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
};

export type ApiKeyCreated = ApiKeyInfo & {
  key: string;  // Only returned once when created
};

export const createApiKey = (name: string, expiresInDays?: number) =>
  request<ApiKeyCreated>("/api-keys", {
    method: "POST",
    body: JSON.stringify({ name, expires_in_days: expiresInDays }),
  });

export const listApiKeys = () =>
  request<ApiKeyInfo[]>("/api-keys");

export const revokeApiKey = (id: number) =>
  request<void>(`/api-keys/${id}`, { method: "DELETE" });

// Analytics
export const getAnalytics = (days = 30) =>
  request<AnalyticsData>(`/analytics?days=${days}`);

// Workflow
export const getPageWorkflow = (pageId: string) =>
  request<PageWithWorkflow>(`/workflow/pages/${pageId}`);

export const submitPageForReview = (pageId: string, comment?: string) =>
  request<{ success: boolean; workflow: unknown; message: string }>(`/workflow/pages/${pageId}/submit`, {
    method: "POST",
    body: JSON.stringify({ comment: comment || null }),
  });

export const startPageReview = (pageId: string, comment?: string) =>
  request<{ success: boolean; workflow: unknown; message: string }>(`/workflow/pages/${pageId}/start-review`, {
    method: "POST",
    body: JSON.stringify({ comment: comment || null }),
  });

export const approvePage = (pageId: string, comment?: string) =>
  request<{ success: boolean; workflow: unknown; message: string }>(`/workflow/pages/${pageId}/approve`, {
    method: "POST",
    body: JSON.stringify({ comment: comment || null }),
  });

export const rejectPage = (pageId: string, reason: string) =>
  request<{ success: boolean; workflow: unknown; message: string }>(`/workflow/pages/${pageId}/reject`, {
    method: "POST",
    body: JSON.stringify({ rejection_reason: reason }),
  });

export const publishPage = (pageId: string, comment?: string) =>
  request<{ success: boolean; workflow: unknown; message: string }>(`/workflow/pages/${pageId}/publish`, {
    method: "POST",
    body: JSON.stringify({ comment: comment || null }),
  });

export const archivePage = (pageId: string, comment?: string) =>
  request<{ success: boolean; workflow: unknown; message: string }>(`/workflow/pages/${pageId}/archive`, {
    method: "POST",
    body: JSON.stringify({ comment: comment || null }),
  });

export const reopenPage = (pageId: string, comment?: string) =>
  request<{ success: boolean; workflow: unknown; message: string }>(`/workflow/pages/${pageId}/reopen`, {
    method: "POST",
    body: JSON.stringify({ comment: comment || null }),
  });

export const getPageVersions = (pageId: string) =>
  request<PageVersion[]>(`/workflow/pages/${pageId}/versions`);

export const getPageAuditLog = (pageId: string) =>
  request<WorkflowAuditLog[]>(`/workflow/pages/${pageId}/audit`);
