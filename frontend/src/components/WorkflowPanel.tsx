import { useState } from "react";
import {
  Send,
  Play,
  CheckCircle,
  XCircle,
  Upload,
  Archive,
  RotateCcw,
  History,
  FileText,
  Loader2,
} from "lucide-react";
import type { WorkflowInfo, WorkflowState, PageVersion, WorkflowAuditLog } from "../types";
import {
  submitPageForReview,
  startPageReview,
  approvePage,
  rejectPage,
  publishPage,
  archivePage,
  reopenPage,
  getPageVersions,
  getPageAuditLog,
} from "../api/client";

const WORKFLOW_STEPS: { state: WorkflowState; label: string }[] = [
  { state: "draft", label: "Draft" },
  { state: "pending_review", label: "Pending Review" },
  { state: "under_review", label: "Under Review" },
  { state: "approved", label: "Approved" },
  { state: "published", label: "Published" },
  { state: "archived", label: "Archived" },
];

const STATE_COLORS: Record<WorkflowState, string> = {
  draft: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  pending_review: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  under_review: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  approved: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  published: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  rejected: "bg-red-500/20 text-red-400 border-red-500/30",
  archived: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

function getStepIndex(state: WorkflowState): number {
  return WORKFLOW_STEPS.findIndex((s) => s.state === state);
}

interface WorkflowPanelProps {
  pageId: string;
  workflow: WorkflowInfo | null | undefined;
  onRefresh: () => void;
}

export default function WorkflowPanel({ pageId, workflow, onRefresh }: WorkflowPanelProps) {
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [versions, setVersions] = useState<PageVersion[]>([]);
  const [auditLog, setAuditLog] = useState<WorkflowAuditLog[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const currentState = workflow?.state || "draft";
  const currentStepIndex = getStepIndex(currentState);

  const handleAction = async (actionFn: () => Promise<unknown>) => {
    setLoading(true);
    try {
      await actionFn();
      onRefresh();
    } catch (e) {
      console.error("Workflow action failed:", e);
    } finally {
      setLoading(false);
      setAction(null);
      setComment("");
    }
  };

  const handleSubmitForReview = () =>
    handleAction(() => submitPageForReview(pageId, comment || undefined));

  const handleStartReview = () =>
    handleAction(() => startPageReview(pageId, comment || undefined));

  const handleApprove = () =>
    handleAction(() => approvePage(pageId, comment || undefined));

  const handleReject = async () => {
    setLoading(true);
    try {
      await rejectPage(pageId, rejectReason);
      onRefresh();
    } catch (e) {
      console.error("Workflow action failed:", e);
    } finally {
      setLoading(false);
      setShowRejectModal(false);
      setRejectReason("");
    }
  };

  const handlePublish = () =>
    handleAction(() => publishPage(pageId, comment || undefined));

  const handleArchive = () =>
    handleAction(() => archivePage(pageId, comment || undefined));

  const handleReopen = () =>
    handleAction(() => reopenPage(pageId, comment || undefined));

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const [vers, log] = await Promise.all([
        getPageVersions(pageId),
        getPageAuditLog(pageId),
      ]);
      setVersions(vers);
      setAuditLog(log);
    } catch (e) {
      console.error("Failed to load history:", e);
    } finally {
      setLoadingHistory(false);
    }
  };

  const toggleHistory = async () => {
    if (!showHistory) {
      await loadHistory();
    }
    setShowHistory(!showHistory);
  };

  const canSubmitForReview = currentState === "draft";
  const canStartReview = currentState === "pending_review";
  const canApprove = currentState === "under_review";
  const canReject = currentState === "under_review";
  const canPublish = currentState === "approved";
  const canArchive = currentState === "published";
  const canReopen = currentState === "rejected" || currentState === "archived";

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[var(--border)]">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-white)]">Workflow</h3>
          <span className={`px-2 py-0.5 rounded text-xs font-medium border ${STATE_COLORS[currentState as WorkflowState] || STATE_COLORS.draft}`}>
            {currentState.replace("_", " ")}
          </span>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="px-4 py-4 border-b border-[var(--border)]">
        <div className="flex items-center justify-between">
          {WORKFLOW_STEPS.slice(0, 5).map((step, idx) => {
            const isCompleted = idx < currentStepIndex;
            const isCurrent = idx === currentStepIndex;
            const isRejected = currentState === "rejected";

            return (
              <div key={step.state} className="flex items-center">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                    isCompleted
                      ? "bg-emerald-500/20 text-emerald-400"
                      : isCurrent && !isRejected
                      ? "bg-blue-500/20 text-blue-400 ring-2 ring-blue-500/30"
                      : isRejected && step.state === "under_review"
                      ? "bg-red-500/20 text-red-400 ring-2 ring-red-500/30"
                      : "bg-zinc-700/30 text-zinc-500"
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle className="w-3.5 h-3.5" />
                  ) : isCurrent || (isRejected && step.state === "under_review") ? (
                    <Play className="w-3 h-3" />
                  ) : (
                    idx + 1
                  )}
                </div>
                {idx < 4 && (
                  <div
                    className={`w-8 sm:w-12 h-0.5 mx-1 ${
                      isCompleted ? "bg-emerald-500/30" : "bg-zinc-700/30"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
        <div className="flex justify-between mt-2">
          {WORKFLOW_STEPS.slice(0, 5).map((step) => (
            <span
              key={step.state}
              className={`text-[10px] ${
                step.state === currentState
                  ? "text-[var(--text-white)] font-medium"
                  : "text-[var(--text-muted)]"
              }`}
            >
              {step.label}
            </span>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="px-4 py-3 border-b border-[var(--border)]">
        <div className="flex flex-wrap gap-2">
          {canSubmitForReview && (
            <button
              onClick={() => setAction("submit")}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-yellow-600 hover:bg-yellow-500 text-white transition-colors disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" /> Submit for Review
            </button>
          )}
          {canStartReview && (
            <button
              onClick={() => setAction("start-review")}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" /> Start Review
            </button>
          )}
          {canApprove && (
            <button
              onClick={() => setAction("approve")}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-50"
            >
              <CheckCircle className="w-3.5 h-3.5" /> Approve
            </button>
          )}
          {canReject && (
            <button
              onClick={() => setShowRejectModal(true)}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-red-600 hover:bg-red-500 text-white transition-colors disabled:opacity-50"
            >
              <XCircle className="w-3.5 h-3.5" /> Reject
            </button>
          )}
          {canPublish && (
            <button
              onClick={() => setAction("publish")}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-600 hover:bg-purple-500 text-white transition-colors disabled:opacity-50"
            >
              <Upload className="w-3.5 h-3.5" /> Publish
            </button>
          )}
          {canArchive && (
            <button
              onClick={() => setAction("archive")}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-600 hover:bg-zinc-500 text-white transition-colors disabled:opacity-50"
            >
              <Archive className="w-3.5 h-3.5" /> Archive
            </button>
          )}
          {canReopen && (
            <button
              onClick={() => setAction("reopen")}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white transition-colors disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Reopen
            </button>
          )}
          <button
            onClick={toggleHistory}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-input)] transition-colors"
          >
            <History className="w-3.5 h-3.5" /> History
          </button>
        </div>

        {/* Comment Input */}
        {action && (
          <div className="mt-3 flex gap-2">
            <input
              type="text"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add a comment (optional)"
              className="flex-1 px-3 py-1.5 text-xs rounded-lg bg-[var(--bg-input)] border border-[var(--border)] text-[var(--text-white)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-icon)]"
            />
            <button
              onClick={() => {
                if (action === "submit") handleSubmitForReview();
                else if (action === "start-review") handleStartReview();
                else if (action === "approve") handleApprove();
                else if (action === "publish") handlePublish();
                else if (action === "archive") handleArchive();
                else if (action === "reopen") handleReopen();
              }}
              disabled={loading}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-[var(--accent-icon)] hover:opacity-90 text-white transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Confirm"}
            </button>
          </div>
        )}
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="p-4 border-t border-[var(--border)] bg-red-950/10">
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-2">
            Rejection Reason (required)
          </label>
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Explain why this page is being rejected..."
            className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-input)] border border-[var(--border)] text-[var(--text-white)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-red-500 resize-none"
            rows={2}
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => setShowRejectModal(false)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-input)] transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleReject}
              disabled={loading || !rejectReason.trim()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-red-600 hover:bg-red-500 text-white transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />}
              Reject Page
            </button>
          </div>
        </div>
      )}

      {/* History Panel */}
      {showHistory && (
        <div className="p-4">
          {loadingHistory ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-5 h-5 animate-spin text-[var(--text-muted)]" />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Versions */}
              <div>
                <h4 className="text-xs font-semibold text-[var(--text-secondary)] mb-2 flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" /> Versions ({versions.length})
                </h4>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {versions.slice(0, 5).map((v) => (
                    <div
                      key={v.id}
                      className="flex items-center justify-between px-2 py-1 rounded bg-[var(--bg-input)] text-xs"
                    >
                      <span className="text-[var(--text-white)]">v{v.version}</span>
                      <span className="text-[var(--text-muted)] truncate max-w-[150px]">
                        {v.change_summary || "No summary"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Audit Log */}
              <div>
                <h4 className="text-xs font-semibold text-[var(--text-secondary)] mb-2 flex items-center gap-1">
                  <History className="w-3.5 h-3.5" /> Activity ({auditLog.length})
                </h4>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {auditLog.slice(0, 5).map((log) => (
                    <div
                      key={log.id}
                      className="flex items-center justify-between px-2 py-1 rounded bg-[var(--bg-input)] text-xs"
                    >
                      <span className="text-[var(--accent-icon)] capitalize">{log.action.replace("_", " ")}</span>
                      <span className="text-[var(--text-muted)]">
                        {log.from_state && log.to_state
                          ? `${log.from_state} → ${log.to_state}`
                          : log.to_state || log.from_state || "-"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
