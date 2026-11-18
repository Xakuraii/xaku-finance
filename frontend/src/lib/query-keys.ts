export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
    sessions: ["auth", "sessions"] as const,
  },
  accounts: {
    all: ["accounts"] as const,
    list: (includeArchived?: boolean) => ["accounts", "list", { includeArchived }] as const,
    detail: (id: string) => ["accounts", "detail", id] as const,
  },
  transactions: {
    all: ["transactions"] as const,
    list: (filters?: Record<string, unknown>) => ["transactions", "list", filters] as const,
    detail: (id: string) => ["transactions", "detail", id] as const,
    audit: (id: string) => ["transactions", "audit", id] as const,
  },
  transfers: {
    all: ["transfers"] as const,
    list: (params?: Record<string, unknown>) => ["transfers", "list", params] as const,
    detail: (id: string) => ["transfers", "detail", id] as const,
  },
  notifications: {
    all: ["notifications"] as const,
    list: (filters?: Record<string, unknown>) => ["notifications", "list", filters] as const,
    unreadCount: ["notifications", "unread-count"] as const,
    preferences: ["notifications", "preferences"] as const,
  },
  settings: {
    me: ["settings", "me"] as const,
    workspace: ["settings", "workspace"] as const,
    summary: ["settings", "summary"] as const,
  },
};
