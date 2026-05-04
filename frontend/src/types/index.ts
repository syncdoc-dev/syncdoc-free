export interface User {
  id: number;
  login: string;
  email: string | null;
  name: string | null;
  avatar_url: string | null;
  theme_id?: string | null;
  marketing_opt_in?: boolean;
  organization_id: string;
  role: string;
}

export interface Source {
  id: string;
  type: "terraform" | "docker" | "ansible" | "git" | "ci_cd";
  url: string;
  project_id?: string | null;
  last_synced: string | null;
  created_at: string;
}

export interface SourceInspection {
  source_type: string;
  ok: boolean;
  summary: string;
  matched_files: string[];
  detected_types: string[];
  warnings: string[];
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  created_at: string;
}

export interface OrgMember {
  user_id: number;
  login: string;
  email: string | null;
  role: string;
  created_at: string;
}

export interface GraphNode {
  id: string;
  kind: string;
  name: string;
  source_id: string;
}

export interface GraphEdge {
  id: string;
  from_node_id: string;
  to_node_id: string;
  relation_type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  manual_edges?: ManualGraphEdge[];
  notes?: GraphNote[];
}

export interface ManualGraphEdge {
  id: string;
  from_node_id: string;
  to_node_id: string;
  label: string | null;
  color: string;
}

export interface GraphNote {
  id: string;
  content: string;
  color: string;
  pos_x: number;
  pos_y: number;
  from_node_id: string | null;
  to_node_id: string | null;
  source_id: string | null;
}

export interface SyncRunEventRun {
  id: string;
  source_id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  nodes_added: number;
  nodes_updated: number;
  drift_count: number;
  error_message: string | null;
}

export interface SyncRunEventMessage {
  type: "sync_run";
  event: "queued" | "started" | "completed" | "failed";
  source_id: string;
  source_name: string | null;
  source_type: string | null;
  project_id: string | null;
  task_id?: string | null;
  status?: string;
  run?: SyncRunEventRun;
  timestamp: string;
}

export interface DriftAlertItem {
  node_name: string;
  node_kind: string;
  diff: Record<string, unknown>;
}

export interface DriftAlertEventMessage {
  type: "drift_alert";
  event: "detected";
  source_id: string;
  source_name: string | null;
  source_type: string | null;
  project_id: string | null;
  run_id: string;
  drift_count: number;
  items: DriftAlertItem[];
  timestamp: string;
}

export interface SyncPingEventMessage {
  type: "ping";
}

export type SyncEventMessage =
  | SyncRunEventMessage
  | DriftAlertEventMessage
  | SyncPingEventMessage;

export interface DriftEvent {
  id: string;
  node_id: string;
  node_name: string | null;
  node_kind: string | null;
  page_id: string | null;
  detected_at: string;
  diff_json: {
    added?: Record<string, unknown>;
    removed?: Record<string, unknown>;
    changed?: Record<string, { old: unknown; new: unknown }>;
  };
  resolved: number;
  resolved_at: string | null;
  resolution_notes: string | null;
  created_at: string;
}

export interface DriftStats {
  total: number;
  unresolved: number;
  resolved: number;
}

export interface SearchNodeResult {
  id: string;
  kind: string;
  name: string;
  source_id: string;
  match_type: "node";
}

export interface SearchPageResult {
  id: string;
  title: string;
  source_id: string | null;
  snippet: string;
  match_type: "page";
}

export interface SearchResults {
  query: string;
  search_mode: "semantic" | "keyword";
  nodes: SearchNodeResult[];
  pages: SearchPageResult[];
}

export interface AppSettings {
  llm_provider: string;
  llm_model: string;
  llm_endpoint_url: string;
  llm_api_key: string | null;
  notification_type: string | null;
  slack_webhook_url: string | null;
  github_token: string | null;
}

export interface Page {
  id: string;
  source_id: string | null;
  title: string;
  content_md: string;
  version: number;
  is_manually_edited: number;
  created_at: string;
  updated_at: string;
  workflow?: WorkflowInfo | null;
}

export type WorkflowState =
  | "draft"
  | "pending_review"
  | "under_review"
  | "approved"
  | "published"
  | "rejected"
  | "archived";

export interface WorkflowInfo {
  id: string;
  page_id: string;
  state: WorkflowState;
  submitted_by_id: number | null;
  reviewed_by_id: number | null;
  approved_by_id: number | null;
  published_by_id: number | null;
  review_comment: string | null;
  rejection_reason: string | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  approved_at: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PageWithWorkflow extends Page {
  workflow: WorkflowInfo | null;
}

export interface PageVersion {
  id: string;
  page_id: string;
  version: number;
  title: string;
  content_md: string;
  changed_by_id: number | null;
  change_summary: string | null;
  workflow_state: string | null;
  created_at: string;
}

export interface WorkflowAuditLog {
  id: string;
  page_id: string;
  workflow_id: string;
  action: string;
  from_state: string | null;
  to_state: string | null;
  actor_id: number | null;
  comment: string | null;
  created_at: string;
}

export interface OwnerExplorerResource {
  key: string;
  label: string;
}

export interface OwnerExplorerListResponse {
  resource: string;
  label: string;
  columns: string[];
  total: number;
  limit: number;
  offset: number;
  items: Array<Record<string, unknown>>;
}

export interface OwnerExplorerDetailResponse {
  resource: string;
  label: string;
  item: Record<string, unknown>;
}

export interface LicenseRecord {
  organization_id: string;
  license_id: string | null;
  plan: string;
  issued_at: string | null;
  expires_at: string | null;
  status: string;
  last_validated_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  enforcement_enabled: boolean;
}

export interface Entitlements {
  plan: string;
  status: string;
  enforcement_enabled: boolean;
  issued_at: string | null;
  expires_at: string | null;
  features: string[];
  limits: Record<string, number>;
  metadata: Record<string, unknown>;
}

export interface UsageStats {
  total_sources: number;
  total_nodes: number;
  total_pages: number;
  total_drift_events: number;
  total_sync_runs: number;
  pages_created_this_week: number;
  sources_synced_this_week: number;
  drift_events_this_week: number;
}

export interface SyncFrequencyPoint {
  date: string;
  count: number;
  successful: number;
  failed: number;
  nodes_added: number;
  nodes_updated: number;
}

export interface DriftTrendPoint {
  date: string;
  detected: number;
  resolved: number;
}

export interface SourceCoverage {
  source_id: string;
  source_name: string;
  source_type: string;
  node_count: number;
  page_count: number;
  last_synced: string | null;
  drift_count: number;
}

export interface PageCoverageStats {
  total_pages: number;
  pages_with_source: number;
  manually_edited: number;
  auto_generated: number;
  sources: SourceCoverage[];
}

export interface AnalyticsData {
  usage_stats: UsageStats;
  sync_frequency: SyncFrequencyPoint[];
  drift_trends: DriftTrendPoint[];
  page_coverage: PageCoverageStats;
}
