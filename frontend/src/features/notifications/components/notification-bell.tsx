import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { getUnreadCount } from "../api/notifications-api";
import { NotificationDrawer } from "./notification-drawer";
import { queryKeys } from "@/lib/query-keys";

export const NotificationBell: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  const { data } = useQuery({
    queryKey: queryKeys.notifications.unreadCount,
    queryFn: getUnreadCount,
    refetchInterval: 30000,
  });

  const unreadCount = data?.unread_count ?? 0;

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        aria-label={
          unreadCount > 0
            ? `${unreadCount} unread notification${unreadCount === 1 ? "" : "s"}`
            : "Notifications"
        }
        className="relative p-2 rounded-lg text-muted hover:text-main hover:bg-[var(--surface-raised)] transition-colors cursor-pointer focus:outline-hidden focus:ring-2 focus:ring-primary"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span
            data-testid="notification-badge"
            className="absolute top-1 right-1 flex items-center justify-center min-w-4 h-4 px-1 rounded-full text-[10px] font-bold bg-negative text-white leading-none shadow-xs"
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      <NotificationDrawer
        open={isOpen}
        onOpenChange={setIsOpen}
        unreadCount={unreadCount}
      />
    </>
  );
};
