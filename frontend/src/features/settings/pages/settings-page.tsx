import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  User,
  Building,
  Bell,
  Check,
  Save,
  AlertCircle,
  Lock,
  Layers,
  Shield,
  KeyRound,
  FileText,
  Download,
  ShieldAlert,
} from "lucide-react";
import {
  getMe,
  updateMe,
  getWorkspaceSettings,
  updateWorkspaceSettings,
  getWorkspaceSummary,
  UserProfileData,
  WorkspaceSettingsData,
} from "../api/settings-api";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
  NotificationPreferenceItem,
} from "@/features/notifications/api/notifications-api";
import {
  getDataMap,
  getExports,
  getCurrentDeletionRequest,
  cancelAccountDeletion,
} from "@/features/privacy/api/privacy-api";
import { ThemeToggle, ThemeMode } from "@/components/theme-toggle";
import { queryKeys } from "@/lib/query-keys";
import { TwoFactorSetupDialog } from "@/features/auth/components/two-factor-setup-dialog";
import { TwoFactorDisableDialog } from "@/features/auth/components/two-factor-disable-dialog";
import { RecoveryCodesDialog } from "@/features/auth/components/recovery-codes-dialog";
import { DataExportDialog } from "@/features/privacy/components/data-export-dialog";
import { AccountDeletionDialog } from "@/features/privacy/components/account-deletion-dialog";

type SettingsTab = "profile" | "workspace" | "security" | "privacy" | "notifications";

export const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const [isSetupOpen, setIsSetupOpen] = useState(false);
  const [isDisableOpen, setIsDisableOpen] = useState(false);
  const [isRecoveryOpen, setIsRecoveryOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(
    null
  );

  const queryClient = useQueryClient();

  // Queries
  const { data: meData, isLoading: isMeLoading } = useQuery({
    queryKey: queryKeys.settings.me,
    queryFn: getMe,
  });

  const { data: wsData, isLoading: isWsLoading } = useQuery({
    queryKey: queryKeys.settings.workspace,
    queryFn: getWorkspaceSettings,
  });

  const { data: summaryData } = useQuery({
    queryKey: queryKeys.settings.summary,
    queryFn: getWorkspaceSummary,
  });

  const { data: notifPrefs = [], isLoading: isPrefsLoading } = useQuery({
    queryKey: queryKeys.notifications.preferences,
    queryFn: getNotificationPreferences,
  });

  const { data: dataMap = [] } = useQuery({
    queryKey: ["privacy", "data-map"],
    queryFn: getDataMap,
  });

  const { data: exportsList = [] } = useQuery({
    queryKey: ["privacy", "exports"],
    queryFn: getExports,
  });

  const { data: deletionRequest } = useQuery({
    queryKey: ["privacy", "deletion-request"],
    queryFn: getCurrentDeletionRequest,
  });

  const cancelDeletionMutation = useMutation({
    mutationFn: cancelAccountDeletion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["privacy", "deletion-request"] });
      setFeedback({ type: "success", message: "Account deletion request has been cancelled." });
    },
    onError: () => {
      setFeedback({ type: "error", message: "Failed to cancel account deletion request." });
    },
  });

  // Local state for forms
  const [profileForm, setProfileForm] = useState<Partial<UserProfileData>>({});
  const [wsForm, setWsForm] = useState<Partial<WorkspaceSettingsData>>({});
  const [prefsForm, setPrefsForm] = useState<NotificationPreferenceItem[]>([]);

  useEffect(() => {
    if (meData) {
      setProfileForm({
        display_name: meData.display_name,
        timezone: meData.timezone,
        locale: meData.locale,
        theme: meData.theme,
      });
    }
  }, [meData]);

  useEffect(() => {
    if (wsData) {
      setWsForm({
        name: wsData.name,
        reporting_currency: wsData.reporting_currency,
        timezone: wsData.timezone,
        week_start: wsData.week_start,
      });
    }
  }, [wsData]);

  useEffect(() => {
    if (notifPrefs.length > 0) {
      setPrefsForm([...notifPrefs]);
    }
  }, [notifPrefs]);

  // Mutations
  const updateMeMutation = useMutation({
    mutationFn: updateMe,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings.me });
      setFeedback({ type: "success", message: "Profile settings saved successfully." });
    },
    onError: (err: any) => {
      setFeedback({
        type: "error",
        message: err?.message || "Failed to update profile settings.",
      });
    },
  });

  const updateWsMutation = useMutation({
    mutationFn: updateWorkspaceSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings.workspace });
      queryClient.invalidateQueries({ queryKey: queryKeys.settings.summary });
      setFeedback({ type: "success", message: "Workspace settings saved successfully." });
    },
    onError: (err: any) => {
      setFeedback({
        type: "error",
        message: err?.message || "Failed to update workspace settings.",
      });
    },
  });

  const updatePrefsMutation = useMutation({
    mutationFn: updateNotificationPreferences,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.preferences });
      setFeedback({ type: "success", message: "Notification preferences saved successfully." });
    },
    onError: (err: any) => {
      setFeedback({
        type: "error",
        message: err?.message || "Failed to update notification preferences.",
      });
    },
  });

  const handleProfileSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    updateMeMutation.mutate(profileForm);
  };

  const handleWsSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    updateWsMutation.mutate(wsForm);
  };

  const handlePrefsSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    updatePrefsMutation.mutate(prefsForm);
  };

  const handlePrefToggle = (category: string, field: "in_app" | "email") => {
    setPrefsForm((prev) =>
      prev.map((item) => {
        if (item.category === category) {
          if (category === "security" && field === "in_app") return item; // locked
          return { ...item, [field]: !item[field] };
        }
        return item;
      })
    );
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8 animate-in fade-in duration-150">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings & Preferences</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your personal profile, workspace defaults, and delivery preferences.
        </p>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div
          role="status"
          className={`p-4 rounded-xl flex items-center justify-between text-sm ${
            feedback.type === "success"
              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
              : "bg-destructive/10 text-destructive border border-destructive/20"
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === "success" ? (
              <Check className="w-4 h-4" />
            ) : (
              <AlertCircle className="w-4 h-4" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="text-xs underline hover:opacity-80 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-border pb-3">
        <button
          type="button"
          onClick={() => setActiveTab("profile")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
            activeTab === "profile"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-muted"
          }`}
        >
          <User className="w-4 h-4" />
          <span>Profile</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("workspace")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
            activeTab === "workspace"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-muted"
          }`}
        >
          <Building className="w-4 h-4" />
          <span>Workspace</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("security")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
            activeTab === "security"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-muted"
          }`}
        >
          <Shield className="w-4 h-4" />
          <span>Security</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("privacy")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
            activeTab === "privacy"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-muted"
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Privacy & Data</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("notifications")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
            activeTab === "notifications"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-muted"
          }`}
        >
          <Bell className="w-4 h-4" />
          <span>Notifications</span>
        </button>
      </div>

      {/* TAB CONTENT: PROFILE */}
      {activeTab === "profile" && (
        <form onSubmit={handleProfileSubmit} className="space-y-6 max-w-xl">
          <div className="bg-card p-6 rounded-2xl border border-border shadow-xs space-y-4">
            <h2 className="text-base font-semibold flex items-center gap-2">
              <User className="w-4 h-4 text-primary" /> Personal Profile
            </h2>

            <div>
              <label htmlFor="display_name" className="block text-xs font-medium text-muted-foreground mb-1">
                Display Name
              </label>
              <input
                id="display_name"
                type="text"
                value={profileForm.display_name ?? ""}
                onChange={(e) => setProfileForm({ ...profileForm, display_name: e.target.value })}
                required
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-hidden focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-xs font-medium text-muted-foreground mb-1">
                Account Email
              </label>
              <input
                id="email"
                type="email"
                value={meData?.email ?? ""}
                disabled
                className="w-full px-3 py-2 rounded-lg border border-border bg-muted/40 text-muted-foreground text-sm cursor-not-allowed"
              />
              <span className="text-[11px] text-muted-foreground mt-1 block">
                {meData?.is_email_verified ? "Verified email address" : "Email pending verification"}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="timezone" className="block text-xs font-medium text-muted-foreground mb-1">
                  Timezone
                </label>
                <input
                  id="timezone"
                  type="text"
                  value={profileForm.timezone ?? ""}
                  onChange={(e) => setProfileForm({ ...profileForm, timezone: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-hidden focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label htmlFor="locale" className="block text-xs font-medium text-muted-foreground mb-1">
                  Locale
                </label>
                <input
                  id="locale"
                  type="text"
                  value={profileForm.locale ?? ""}
                  onChange={(e) => setProfileForm({ ...profileForm, locale: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-hidden focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <div className="pt-2">
              <label className="block text-xs font-medium text-muted-foreground mb-2">
                Color Theme
              </label>
              <ThemeToggle
                value={profileForm.theme as ThemeMode}
                onChange={(theme) => setProfileForm({ ...profileForm, theme })}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={updateMeMutation.isPending || isMeLoading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 shadow-xs transition-opacity cursor-pointer disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{updateMeMutation.isPending ? "Saving..." : "Save Profile"}</span>
          </button>
        </form>
      )}

      {/* TAB CONTENT: WORKSPACE */}
      {activeTab === "workspace" && (
        <div className="space-y-8 max-w-3xl">
          <form onSubmit={handleWsSubmit} className="space-y-6 max-w-xl">
            <div className="bg-card p-6 rounded-2xl border border-border shadow-xs space-y-4">
              <h2 className="text-base font-semibold flex items-center gap-2">
                <Building className="w-4 h-4 text-primary" /> Workspace Configuration
              </h2>

              <div>
                <label htmlFor="ws_name" className="block text-xs font-medium text-muted-foreground mb-1">
                  Workspace Name
                </label>
                <input
                  id="ws_name"
                  type="text"
                  value={wsForm.name ?? ""}
                  onChange={(e) => setWsForm({ ...wsForm, name: e.target.value })}
                  required
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-hidden focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="reporting_currency" className="block text-xs font-medium text-muted-foreground mb-1">
                    Reporting Currency
                  </label>
                  <input
                    id="reporting_currency"
                    type="text"
                    value={wsForm.reporting_currency ?? ""}
                    onChange={(e) =>
                      setWsForm({ ...wsForm, reporting_currency: e.target.value.toUpperCase() })
                    }
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-hidden focus:ring-2 focus:ring-primary uppercase"
                  />
                  <span className="text-[11px] text-muted-foreground mt-1 block">
                    Base currency for analytics and net worth.
                  </span>
                </div>

                <div>
                  <label htmlFor="week_start" className="block text-xs font-medium text-muted-foreground mb-1">
                    First Day of Week
                  </label>
                  <select
                    id="week_start"
                    value={wsForm.week_start ?? 1}
                    onChange={(e) => setWsForm({ ...wsForm, week_start: Number(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-hidden focus:ring-2 focus:ring-primary"
                  >
                    <option value={1}>Monday (ISO)</option>
                    <option value={7}>Sunday</option>
                    <option value={6}>Saturday</option>
                  </select>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={updateWsMutation.isPending || isWsLoading}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 shadow-xs transition-opacity cursor-pointer disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{updateWsMutation.isPending ? "Saving..." : "Save Workspace"}</span>
            </button>
          </form>

          {/* Diagnostic Workspace Summary */}
          {summaryData && (
            <div className="bg-card p-6 rounded-2xl border border-border shadow-xs space-y-4">
              <h3 className="text-sm font-semibold flex items-center gap-2 text-foreground">
                <Layers className="w-4 h-4 text-primary" /> Workspace Diagnostics
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                <div className="p-3 rounded-xl bg-muted/30 border border-border">
                  <span className="text-[11px] text-muted-foreground block">Accounts</span>
                  <span className="text-lg font-bold text-foreground">{summaryData.accounts_count}</span>
                </div>
                <div className="p-3 rounded-xl bg-muted/30 border border-border">
                  <span className="text-[11px] text-muted-foreground block">Transactions</span>
                  <span className="text-lg font-bold text-foreground">
                    {summaryData.transactions_count}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-muted/30 border border-border">
                  <span className="text-[11px] text-muted-foreground block">Budgets</span>
                  <span className="text-lg font-bold text-foreground">{summaryData.budgets_count}</span>
                </div>
                <div className="p-3 rounded-xl bg-muted/30 border border-border">
                  <span className="text-[11px] text-muted-foreground block">Savings Goals</span>
                  <span className="text-lg font-bold text-foreground">
                    {summaryData.savings_goals_count}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-muted/30 border border-border">
                  <span className="text-[11px] text-muted-foreground block">Ledger Sequence</span>
                  <span className="text-lg font-bold text-foreground">{summaryData.ledger_seq}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: SECURITY */}
      {activeTab === "security" && (
        <div className="space-y-6 max-w-2xl">
          {/* 2FA Card */}
          <div className="bg-card p-6 rounded-2xl border border-border shadow-xs space-y-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <Shield className="w-4 h-4 text-primary" /> Two-Factor Authentication (TOTP)
                </h2>
                <p className="text-xs text-muted-foreground mt-1">
                  Add an extra layer of protection to your workspace using an authenticator app (Google Authenticator, 1Password, etc.).
                </p>
              </div>

              {meData?.two_factor_enabled ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 shrink-0">
                  <Check className="w-3.5 h-3.5" />
                  Active
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20 shrink-0">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Disabled
                </span>
              )}
            </div>

            {meData?.two_factor_enabled ? (
              <div className="space-y-4 pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground">
                  Your account is protected with two-factor authentication. You will be prompted for a 6-digit one-time code each time you sign in.
                </p>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setIsRecoveryOpen(true)}
                    className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl border border-border bg-card hover:bg-muted text-xs font-medium text-foreground transition-colors cursor-pointer"
                  >
                    <KeyRound className="w-3.5 h-3.5 text-primary" />
                    <span>Regenerate Recovery Codes</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsDisableOpen(true)}
                    className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl border border-destructive/30 bg-destructive/5 hover:bg-destructive/10 text-xs font-medium text-destructive transition-colors cursor-pointer"
                  >
                    <span>Disable 2FA</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4 pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground">
                  When enabled, you will need your password and a verification code from your mobile device to sign in.
                </p>

                <button
                  type="button"
                  onClick={() => setIsSetupOpen(true)}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 shadow-xs transition-opacity cursor-pointer"
                >
                  <Shield className="w-3.5 h-3.5" />
                  <span>Enable Two-Factor Authentication</span>
                </button>
              </div>
            )}
          </div>

          {/* Session & Password Policy Card */}
          <div className="bg-card p-6 rounded-2xl border border-border shadow-xs space-y-4">
            <h3 className="text-sm font-semibold flex items-center gap-2 text-foreground">
              <Lock className="w-4 h-4 text-primary" /> Security & Re-authentication Policy
            </h3>
            <div className="space-y-3 text-xs text-muted-foreground leading-relaxed">
              <p>
                • <strong>Step-Up Re-authentication:</strong> Sensitive operations such as exporting financial data, modifying two-factor settings, and requesting account deletion require confirming your password within the past 10 minutes.
              </p>
              <p>
                • <strong>Session Privacy:</strong> Your active session tokens rotate automatically. IP addresses are hashed using HMAC-SHA256 and never logged or exposed in raw form.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: PRIVACY & DATA */}
      {activeTab === "privacy" && (
        <div className="space-y-6 max-w-3xl">
          {/* Data Export Card */}
          <div className="bg-card p-6 rounded-2xl border border-border shadow-xs space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <Download className="w-4 h-4 text-primary" /> Data Export & Portability
                </h2>
                <p className="text-xs text-muted-foreground mt-1">
                  Export your entire workspace data or select specific datasets in JSON or CSV format. Requires password re-authentication.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setIsExportOpen(true)}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 shadow-xs transition-opacity cursor-pointer shrink-0"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Data</span>
              </button>
            </div>

            {exportsList.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-border">
                <span className="text-xs font-semibold text-foreground block">Recent Exports</span>
                <div className="divide-y divide-border">
                  {exportsList.map((job) => (
                    <div key={job.id} className="py-2.5 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-semibold text-foreground uppercase">{job.format}</span>
                        <span className="text-muted-foreground ml-2 capitalize">({job.scope})</span>
                        <span className="text-[11px] text-muted-foreground block">
                          {new Date(job.created_at).toLocaleDateString()} • {(job.file_size_bytes / 1024).toFixed(1)} KB
                        </span>
                      </div>

                      {job.download_url && job.status === "completed" ? (
                        <a
                          href={job.download_url}
                          download
                          className="px-3 py-1 rounded-lg border border-border bg-card hover:bg-muted font-medium text-foreground flex items-center gap-1 transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>Download</span>
                        </a>
                      ) : (
                        <span className="text-muted-foreground capitalize">{job.status}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Transparency Data Map */}
          <div className="bg-card p-6 rounded-2xl border border-border shadow-xs space-y-4">
            <h2 className="text-base font-semibold flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary" /> Data Transparency Map
            </h2>
            <p className="text-xs text-muted-foreground">
              What data we store, the purposes for which it is processed, and our retention schedules.
            </p>

            <div className="space-y-3 pt-2">
              {dataMap.map((item, i) => (
                <div key={i} className="p-3.5 rounded-xl bg-muted/30 border border-border space-y-1.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">{item.category}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                      {item.lawful_basis}
                    </span>
                  </div>
                  <p className="text-muted-foreground leading-relaxed">{item.description}</p>
                  <div className="pt-1 text-[11px] text-primary flex items-center gap-1.5">
                    <strong>Retention:</strong>
                    <span>{item.retention}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Danger Zone: Account Deletion */}
          <div className="bg-card p-6 rounded-2xl border border-destructive/30 shadow-xs space-y-4">
            <h2 className="text-base font-semibold flex items-center gap-2 text-destructive">
              <ShieldAlert className="w-4 h-4 text-destructive" /> Danger Zone: Account Deletion
            </h2>

            {deletionRequest && deletionRequest.status === "requested" ? (
              <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/30 space-y-3">
                <div className="text-xs text-destructive space-y-1">
                  <p className="font-semibold">Account Deletion Scheduled</p>
                  <p>
                    Your account and all workspace data are scheduled for permanent deletion on{" "}
                    <strong>{new Date(deletionRequest.execute_after).toLocaleString()}</strong>.
                  </p>
                  <p className="text-[11px]">
                    Encrypted system backups containing your data will expire by{" "}
                    <strong>{deletionRequest.backup_expiry_date}</strong>.
                  </p>
                </div>

                <button
                  type="button"
                  disabled={cancelDeletionMutation.isPending}
                  onClick={() => cancelDeletionMutation.mutate()}
                  className="px-3.5 py-2 rounded-xl bg-card border border-destructive/40 text-xs font-semibold text-destructive hover:bg-destructive/10 transition-colors cursor-pointer disabled:opacity-50"
                >
                  {cancelDeletionMutation.isPending ? "Cancelling..." : "Cancel Deletion Request"}
                </button>
              </div>
            ) : (
              <div className="flex items-start justify-between gap-4">
                <div className="text-xs text-muted-foreground space-y-1">
                  <p>
                    Permanently delete your account, workspace, ledger, and all financial transactions.
                  </p>
                  <p className="text-[11px]">
                    Includes a 7-day grace period. Truthful backup retention disclosure: Encrypted backups expire after 30 days.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => setIsDeleteOpen(true)}
                  className="px-4 py-2 rounded-xl bg-destructive text-white text-xs font-semibold hover:opacity-90 transition-opacity cursor-pointer shrink-0"
                >
                  Delete Account
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT: NOTIFICATIONS */}
      {activeTab === "notifications" && (
        <form onSubmit={handlePrefsSubmit} className="space-y-6 max-w-2xl">
          <div className="bg-card p-6 rounded-2xl border border-border shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <Bell className="w-4 h-4 text-primary" /> Delivery Channels
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Configure how alerts reach you. Security warnings are locked for safety.
                </p>
              </div>
            </div>

            <div className="divide-y divide-border">
              {prefsForm.map((pref) => (
                <div key={pref.id} className="py-3 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    {pref.category === "security" ? (
                      <div className="p-2 rounded-lg bg-destructive/10 text-destructive">
                        <Lock className="w-4 h-4" />
                      </div>
                    ) : (
                      <div className="p-2 rounded-lg bg-primary/10 text-primary">
                        <Bell className="w-4 h-4" />
                      </div>
                    )}
                    <div>
                      <span className="text-sm font-semibold capitalize text-foreground">
                        {pref.category === "bill" ? "Bills & Recurring" : pref.category}
                      </span>
                      {pref.category === "security" && (
                        <span className="block text-[11px] text-destructive font-medium">
                          Security notifications are locked to active
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <label className="flex items-center gap-2 text-xs font-medium text-foreground cursor-pointer">
                      <input
                        type="checkbox"
                        checked={pref.in_app}
                        disabled={pref.locked || pref.category === "security"}
                        onChange={() => handlePrefToggle(pref.category, "in_app")}
                        className="rounded border-border text-primary focus:ring-primary w-4 h-4 disabled:opacity-60"
                      />
                      <span>In-App</span>
                    </label>

                    <label className="flex items-center gap-2 text-xs font-medium text-foreground cursor-pointer">
                      <input
                        type="checkbox"
                        checked={pref.email}
                        onChange={() => handlePrefToggle(pref.category, "email")}
                        className="rounded border-border text-primary focus:ring-primary w-4 h-4"
                      />
                      <span>Email</span>
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={updatePrefsMutation.isPending || isPrefsLoading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 shadow-xs transition-opacity cursor-pointer disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{updatePrefsMutation.isPending ? "Saving..." : "Save Preferences"}</span>
          </button>
        </form>
      )}

      {/* 2FA Modals */}
      <TwoFactorSetupDialog
        isOpen={isSetupOpen}
        onClose={() => setIsSetupOpen(false)}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: queryKeys.settings.me });
          setFeedback({
            type: "success",
            message: "Two-factor authentication has been enabled successfully!",
          });
        }}
      />

      <TwoFactorDisableDialog
        isOpen={isDisableOpen}
        onClose={() => setIsDisableOpen(false)}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: queryKeys.settings.me });
          setFeedback({
            type: "success",
            message: "Two-factor authentication has been disabled.",
          });
        }}
      />

      <RecoveryCodesDialog
        isOpen={isRecoveryOpen}
        onClose={() => setIsRecoveryOpen(false)}
      />

      {/* Privacy Modals */}
      <DataExportDialog
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ["privacy", "exports"] });
          setFeedback({
            type: "success",
            message: "Workspace data export generated successfully.",
          });
        }}
      />

      <AccountDeletionDialog
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        twoFactorEnabled={meData?.two_factor_enabled}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ["privacy", "deletion-request"] });
          setFeedback({
            type: "success",
            message: "Account deletion request has been registered with a 7-day grace period.",
          });
        }}
      />
    </div>
  );
};
