import React, { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  X,
  CheckCheck,
  AlertTriangle,
  AlertCircle,
  Info,
  ShieldAlert,
  PiggyBank,
  Receipt,
  Check,
} from "lucide-react";
import {
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  NotificationItem,
} from "../api/notifications-api";
import { queryKeys } from "@/lib/query-keys";

interface NotificationDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  unreadCount: number;
}

type FilterCategory = "all" | "unread" | "budget" | "bill" | "savings" | "security";

export const NotificationDrawer: React.FC<NotificationDrawerProps> = ({
  open,
  onOpenChange,
  unreadCount,
}) => {
  const [filter, setFilter] = useState<FilterCategory>("all");
  const queryClient = useQueryClient();

  const { data: notifications = [], isLoading } = useQuery({
    queryKey: queryKeys.notifications.list({
      unread: filter === "unread" ? true : undefined,
      category: ["budget", "bill", "savings", "security"].includes(filter) ? filter : undefined,
    }),
    queryFn: () =>
      getNotifications({
        unread: filter === "unread" ? true : undefined,
        category: ["budget", "bill", "savings", "security"].includes(filter) ? filter : undefined,
      }),
    enabled: open,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.unreadCount });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.unreadCount });
    },
  });

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "budget":
        return <AlertTriangle className="w-4 h-4 text-warning" />;
      case "bill":
        return <Receipt className="w-4 h-4 text-primary" />;
      case "savings":
        return <PiggyBank className="w-4 h-4 text-emerald-500" />;
      case "security":
        return <ShieldAlert className="w-4 h-4 text-destructive" />;
      default:
        return <Info className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "critical":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-destructive/10 text-destructive border border-destructive/20">
            <AlertCircle className="w-3 h-3" /> Critical
          </span>
        );
      case "warning":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-warning/10 text-warning border border-warning/20">
            <AlertTriangle className="w-3 h-3" /> Warning
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">
            <Info className="w-3 h-3" /> Info
          </span>
        );
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50 backdrop-blur-xs animate-in fade-in" />
        <Dialog.Content
          className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-card text-card-foreground shadow-2xl z-50 border-l border-border flex flex-col animate-in slide-in-from-right duration-200"
          aria-describedby="notification-drawer-description"
        >
          {/* Header */}
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <Bell className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <Dialog.Title className="text-base font-semibold">Notifications</Dialog.Title>
                  {unreadCount > 0 && (
                    <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-primary text-primary-foreground">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                <p id="notification-drawer-description" className="text-xs text-muted-foreground">
                  Financial alerts, budget thresholds, and reminders
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={() => markAllReadMutation.mutate()}
                  disabled={markAllReadMutation.isPending}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                  title="Mark all notifications as read"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Mark all read</span>
                </button>
              )}
              <Dialog.Close className="p-1.5 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer">
                <X className="w-5 h-5" />
              </Dialog.Close>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="px-4 py-2 border-b border-border bg-muted/20 flex items-center gap-1.5 overflow-x-auto text-xs">
            {(
              [
                { id: "all", label: "All" },
                { id: "unread", label: "Unread" },
                { id: "budget", label: "Budgets" },
                { id: "bill", label: "Bills" },
                { id: "savings", label: "Savings" },
                { id: "security", label: "Security" },
              ] as const
            ).map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setFilter(item.id)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors whitespace-nowrap cursor-pointer ${
                  filter === item.id
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* List Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center h-48 text-muted-foreground gap-2">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                <span className="text-xs">Loading alerts...</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-56 text-center text-muted-foreground px-4">
                <div className="w-12 h-12 rounded-full bg-muted/50 flex items-center justify-center mb-3">
                  <Bell className="w-6 h-6 text-muted-foreground/60" />
                </div>
                <h4 className="text-sm font-semibold text-foreground">You're all caught up</h4>
                <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                  {filter === "unread"
                    ? "No unread notifications at this time."
                    : "No notifications matching this filter."}
                </p>
              </div>
            ) : (
              notifications.map((notif: NotificationItem) => (
                <div
                  key={notif.id}
                  className={`p-3.5 rounded-xl border transition-all ${
                    notif.read_at
                      ? "bg-card/40 border-border/60 opacity-80"
                      : "bg-card border-primary/20 shadow-xs hover:border-primary/40"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5 flex-1">
                      <div className="mt-0.5 p-1 rounded-md bg-muted/60">
                        {getCategoryIcon(notif.category)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className="text-xs font-semibold text-foreground truncate">
                            {notif.title}
                          </span>
                          {getSeverityBadge(notif.severity)}
                          {!notif.read_at && (
                            <span className="w-2 h-2 rounded-full bg-primary" title="Unread" />
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {notif.body}
                        </p>
                        <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
                          <span>{formatDate(notif.created_at)}</span>
                          {!notif.read_at && (
                            <button
                              type="button"
                              onClick={() => markReadMutation.mutate(notif.id)}
                              disabled={markReadMutation.isPending}
                              className="inline-flex items-center gap-1 text-primary hover:underline cursor-pointer"
                              title="Mark as read"
                            >
                              <Check className="w-3 h-3" /> Mark read
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
