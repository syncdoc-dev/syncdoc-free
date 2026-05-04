import { useEffect, useMemo, useState } from "react";
import {
  Building2,
  Users,
  Shield,
  Save,
  Plus,
  AlertCircle,
  Trash2,
  KeyRound,
} from "lucide-react";
import {
  createOrganizationUser,
  deleteLicense,
  deleteOrganizationUser,
  getEntitlements,
  getLicense,
  getOrganization,
  getOrganizationMembers,
  installLicense,
  updateOrganization,
  updateOrganizationMemberRole,
} from "../api/client";
import type { Entitlements, LicenseRecord, Organization, OrgMember } from "../types";
import { useAuth } from "../context/AuthContext";
import UpgradeBadge from "../components/UpgradeBadge";

const ROLE_LABELS: Record<string, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
  viewer: "Viewer",
};

const ROLE_BADGE: Record<string, string> = {
  owner: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  admin: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  member: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  viewer: "bg-slate-500/15 text-slate-400 border-slate-500/30",
};

export default function OrganizationPage() {
  const { user, getLimit, refreshEntitlements } = useAuth();
  const canManage = useMemo(
    () => user?.role === "owner" || user?.role === "admin",
    [user?.role]
  );
  const [org, setOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [license, setLicense] = useState<LicenseRecord | null>(null);
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [orgName, setOrgName] = useState("");
  const [licenseToken, setLicenseToken] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [licenseSaving, setLicenseSaving] = useState(false);
  const [error, setError] = useState("");
  const [memberError, setMemberError] = useState("");
  const [licenseError, setLicenseError] = useState("");
  const [licenseMessage, setLicenseMessage] = useState("");
  const [form, setForm] = useState({
    login: "",
    email: "",
    name: "",
    password: "",
    role: "member",
  });
  const [roleUpdating, setRoleUpdating] = useState<Set<number>>(new Set());
  const ownerCount = members.filter((member) => member.role === "owner").length;
  const userLimit = getLimit("users");
  const userLimitReached = userLimit !== null && members.length >= userLimit;

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [orgData, memberData] = await Promise.all([
        getOrganization(),
        getOrganizationMembers(),
      ]);
      setOrg(orgData);
      setOrgName(orgData.name);
      setMembers(memberData);
      try {
        const [licenseData, entitlementData] = await Promise.all([
          getLicense(),
          getEntitlements(),
        ]);
        setLicense(licenseData);
        setEntitlements(entitlementData);
      } catch (licenseErr) {
        setLicenseError(
          licenseErr instanceof Error ? licenseErr.message : "Failed to load license information"
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load organization");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSaveOrg = async () => {
    if (!canManage || !orgName.trim()) return;
    setSaving(true);
    setError("");
    try {
      const updated = await updateOrganization(orgName.trim());
      setOrg(updated);
      setOrgName(updated.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update organization");
    } finally {
      setSaving(false);
    }
  };

  const handleInstallLicense = async () => {
    if (user?.role !== "owner" || !licenseToken.trim()) return;
    setLicenseSaving(true);
    setLicenseError("");
    setLicenseMessage("");
    try {
      const installed = await installLicense(licenseToken.trim());
      const refreshedEntitlements = await getEntitlements();
      setLicense(installed);
      setEntitlements(refreshedEntitlements);
      await refreshEntitlements();
      setLicenseToken("");
      setLicenseMessage("License installed and verified.");
    } catch (err) {
      setLicenseError(err instanceof Error ? err.message : "Failed to install license");
    } finally {
      setLicenseSaving(false);
    }
  };

  const handleDeleteLicense = async () => {
    if (user?.role !== "owner") return;
    const confirmed = window.confirm("Remove the installed license for this organization?");
    if (!confirmed) return;
    setLicenseSaving(true);
    setLicenseError("");
    setLicenseMessage("");
    try {
      await deleteLicense();
      const [licenseData, entitlementData] = await Promise.all([
        getLicense(),
        getEntitlements(),
      ]);
      setLicense(licenseData);
      setEntitlements(entitlementData);
      await refreshEntitlements();
      setLicenseMessage("License removed.");
    } catch (err) {
      setLicenseError(err instanceof Error ? err.message : "Failed to remove license");
    } finally {
      setLicenseSaving(false);
    }
  };

  const handleCreateUser = async () => {
    if (!canManage) return;
    setCreating(true);
    setMemberError("");
    try {
      const payload = {
        login: form.login.trim(),
        password: form.password,
        role: form.role,
        email: form.email.trim() ? form.email.trim() : undefined,
        name: form.name.trim() ? form.name.trim() : undefined,
      };
      await createOrganizationUser(payload);
      setForm({ login: "", email: "", name: "", password: "", role: "member" });
      await load();
    } catch (err) {
      setMemberError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setCreating(false);
    }
  };

  const handleRoleChange = async (member: OrgMember, role: string) => {
    if (!canManage || member.role === role) return;
    setRoleUpdating((prev) => new Set(prev).add(member.user_id));
    setMemberError("");
    try {
      const updated = await updateOrganizationMemberRole(member.user_id, role);
      setMembers((prev) =>
        prev.map((item) => (item.user_id === updated.user_id ? updated : item))
      );
    } catch (err) {
      setMemberError(err instanceof Error ? err.message : "Failed to update role");
    } finally {
      setRoleUpdating((prev) => {
        const next = new Set(prev);
        next.delete(member.user_id);
        return next;
      });
    }
  };

  const canDeleteMember = (member: OrgMember) => {
    if (!canManage) return false;
    if (member.user_id === user?.id) return false;
    if (user?.role !== "owner" && (member.role === "admin" || member.role === "owner")) {
      return false;
    }
    if (member.role === "owner" && ownerCount <= 1) return false;
    return true;
  };

  const handleDeleteMember = async (member: OrgMember) => {
    if (!canDeleteMember(member)) return;
    const confirmed = window.confirm(`Delete user ${member.login}? This cannot be undone.`);
    if (!confirmed) return;
    setMemberError("");
    try {
      await deleteOrganizationUser(member.user_id);
      await load();
    } catch (err) {
      setMemberError(err instanceof Error ? err.message : "Failed to delete user");
    }
  };

  const cardCls =
    "rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6 space-y-4";
  const labelCls = "block text-sm font-medium text-[var(--text-secondary)] mb-1.5";
  const inputCls =
    "w-full rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-strong)] transition-colors";
  const ownerOnly = user?.role === "owner";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-white)] flex items-center gap-2">
            <Building2 className="w-6 h-6" />
            Organization
          </h1>
          <p className="text-[var(--text-secondary)] mt-1">
            Manage organization settings and users
          </p>
        </div>
        {user && (
          <span
            className={`inline-flex items-center rounded-full border px-3 py-1 text-xs uppercase tracking-wide ${
              ROLE_BADGE[user.role] ?? ROLE_BADGE.viewer
            }`}
          >
            {ROLE_LABELS[user.role] ?? user.role}
          </span>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40 text-[var(--text-secondary)]">
          Loading organization...
        </div>
      ) : (
        <>
          <div className={cardCls}>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-[var(--text-muted)]" />
              <h2 className="text-lg font-semibold text-[var(--text-white)]">
                Organization Details
              </h2>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className={labelCls}>Organization name</label>
                <input
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className={inputCls}
                  disabled={!canManage}
                />
              </div>
              <div>
                <label className={labelCls}>Created</label>
                <div className="px-3 py-2 rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] text-sm text-[var(--text-secondary)]">
                  {org?.created_at ? new Date(org.created_at).toLocaleString() : "—"}
                </div>
              </div>
            </div>
            {canManage ? (
              <button
                onClick={handleSaveOrg}
                disabled={saving || !orgName.trim()}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-strong)] hover:bg-[var(--accent-hover)] text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="w-4 h-4" />
                {saving ? "Saving..." : "Save Organization"}
              </button>
            ) : (
              <p className="text-sm text-[var(--text-muted)]">
                You have read-only access to organization settings.
              </p>
            )}
          </div>

          <div className={cardCls}>
            <div className="flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-[var(--text-muted)]" />
              <h2 className="text-lg font-semibold text-[var(--text-white)]">License</h2>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">
              Offline licensing and entitlements for this organization.
            </p>

            {licenseError && (
              <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {licenseError}
              </div>
            )}

            {licenseMessage && (
              <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
                {licenseMessage}
              </div>
            )}

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <label className={labelCls}>Plan</label>
                <div className="rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)]">
                  {entitlements?.plan ?? license?.plan ?? "free"}
                </div>
              </div>
              <div>
                <label className={labelCls}>Status</label>
                <div className="rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)]">
                  {entitlements?.status ?? license?.status ?? "missing"}
                </div>
              </div>
              <div>
                <label className={labelCls}>Enforcement</label>
                <div className="rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)]">
                  {(entitlements?.enforcement_enabled ?? license?.enforcement_enabled)
                    ? "Enabled"
                    : "Disabled"}
                </div>
              </div>
              <div>
                <label className={labelCls}>Expires</label>
                <div className="rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)]">
                  {entitlements?.expires_at || license?.expires_at
                    ? new Date(entitlements?.expires_at ?? license?.expires_at ?? "").toLocaleString()
                    : "No expiry"}
                </div>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div>
                <label className={labelCls}>Features</label>
                <div className="rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] p-3 text-sm text-[var(--text-primary)]">
                  {entitlements?.features?.length ? (
                    <div className="flex flex-wrap gap-2">
                      {entitlements.features.map((feature) => (
                        <span
                          key={feature}
                          className="inline-flex items-center rounded-full border border-[var(--border)] px-2.5 py-1 text-xs text-[var(--text-secondary)]"
                        >
                          {feature}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-[var(--text-muted)]">Free/core features only</span>
                  )}
                </div>
              </div>
              <div>
                <label className={labelCls}>Limits</label>
                <div className="rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] p-3 text-sm text-[var(--text-primary)]">
                  {entitlements ? (
                    <div className="grid gap-2 sm:grid-cols-2">
                      {Object.entries(entitlements.limits).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between gap-3 rounded border border-[var(--border)] px-3 py-2">
                          <span className="text-[var(--text-secondary)]">{key}</span>
                          <span>{value}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="text-[var(--text-muted)]">No entitlement data loaded.</span>
                  )}
                </div>
              </div>
            </div>

            {ownerOnly ? (
              <div className="space-y-4">
                <div>
                  <label className={labelCls}>Install or replace license token</label>
                  <textarea
                    value={licenseToken}
                    onChange={(e) => setLicenseToken(e.target.value)}
                    rows={6}
                    className={`${inputCls} min-h-[140px] resize-y`}
                    placeholder='Paste signed token, or dev JSON token in development mode'
                  />
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={handleInstallLicense}
                    disabled={licenseSaving || !licenseToken.trim()}
                    className="inline-flex items-center gap-2 rounded-lg bg-[var(--accent-strong)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Save className="w-4 h-4" />
                    {licenseSaving ? "Saving..." : "Install License"}
                  </button>
                  <button
                    type="button"
                    onClick={handleDeleteLicense}
                    disabled={licenseSaving || (license?.status ?? "missing") === "missing"}
                    className="inline-flex items-center gap-2 rounded-lg border border-[var(--border-light)] px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:border-red-400/50 hover:bg-red-500/10 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4" />
                    Remove License
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-[var(--text-muted)]">
                Only organization owners can install or remove licenses.
              </p>
            )}
          </div>

          <div className={cardCls}>
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-[var(--text-muted)]" />
              <h2 className="text-lg font-semibold text-[var(--text-white)]">Members</h2>
              {userLimitReached && <UpgradeBadge />}
            </div>

            {memberError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {memberError}
              </div>
            )}

            <div className="space-y-3">
              {members.map((member) => (
                <div
                  key={member.user_id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--border)] px-4 py-3"
                >
                  <div className="min-w-[200px]">
                    <p className="text-sm font-medium text-[var(--text-white)]">
                      {member.login}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      {member.email ?? "No email"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs uppercase tracking-wide ${
                        ROLE_BADGE[member.role] ?? ROLE_BADGE.viewer
                      }`}
                    >
                      {ROLE_LABELS[member.role] ?? member.role}
                    </span>
                    {canManage && (
                      <select
                        value={member.role}
                        onChange={(e) => handleRoleChange(member, e.target.value)}
                        disabled={roleUpdating.has(member.user_id)}
                        className="rounded-lg border border-[var(--border-light)] bg-[var(--bg-input)] px-2 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-strong)]"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="member">Member</option>
                        <option value="admin">Admin</option>
                        <option value="owner">Owner</option>
                      </select>
                    )}
                    {canManage && (
                      <button
                        type="button"
                        onClick={() => handleDeleteMember(member)}
                        disabled={!canDeleteMember(member)}
                        className="inline-flex items-center justify-center rounded-lg border border-[var(--border-light)] px-2 py-1.5 text-xs text-[var(--text-secondary)] hover:text-red-300 hover:border-red-400/50 hover:bg-red-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        title={
                          canDeleteMember(member)
                            ? "Delete user"
                            : "You cannot delete this user"
                        }
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {canManage && (
              <div className="mt-6 space-y-4">
                <div className="flex items-center gap-2">
                  <Plus className="w-4 h-4 text-[var(--text-muted)]" />
                  <h3 className="text-base font-semibold text-[var(--text-white)]">
                    Create User
                  </h3>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className={labelCls}>Login</label>
                    <input
                      value={form.login}
                      onChange={(e) => setForm((prev) => ({ ...prev, login: e.target.value }))}
                      className={inputCls}
                      placeholder="jane.doe"
                      disabled={userLimitReached}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Email</label>
                    <input
                      value={form.email}
                      onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
                      className={inputCls}
                      placeholder="jane@example.com"
                      disabled={userLimitReached}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Name</label>
                    <input
                      value={form.name}
                      onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                      className={inputCls}
                      placeholder="Jane Doe"
                      disabled={userLimitReached}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Password</label>
                    <input
                      type="password"
                      value={form.password}
                      onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
                      className={inputCls}
                      placeholder="Minimum 8 characters"
                      disabled={userLimitReached}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Role</label>
                    <select
                      value={form.role}
                      onChange={(e) => setForm((prev) => ({ ...prev, role: e.target.value }))}
                      className={inputCls}
                      disabled={userLimitReached}
                    >
                      <option value="viewer">Viewer</option>
                      <option value="member">Member</option>
                      <option value="admin">Admin</option>
                      <option value="owner">Owner</option>
                    </select>
                  </div>
                </div>
                <button
                  onClick={handleCreateUser}
                  disabled={
                    creating ||
                    !form.login.trim() ||
                    !form.password ||
                    form.password.length < 8 ||
                    userLimitReached
                  }
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-strong)] hover:bg-[var(--accent-hover)] text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Plus className="w-4 h-4" />
                  {creating ? "Creating..." : "Create User"}
                </button>
                {userLimitReached && (
                  <p className="text-sm text-amber-300">
                    User limit reached for this license. Upgrade to add more members.
                  </p>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
