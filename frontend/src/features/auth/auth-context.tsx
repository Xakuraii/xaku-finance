import React, { createContext, useContext, useEffect, useState } from "react";
import { api, setAccessToken } from "@/lib/api/client";

export interface User {
  id: string;
  email: string;
  is_email_verified: boolean;
  display_name?: string;
}

export interface Workspace {
  id: string;
  name: string;
  reporting_currency: string;
  timezone: string;
}

export interface AuthContextType {
  user: User | null;
  workspace: Workspace | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ mfa_required?: boolean }>;
  register: (payload: {
    email: string;
    password: string;
    display_name?: string;
    reporting_currency?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session on mount via refresh endpoint
  useEffect(() => {
    async function restoreSession() {
      try {
        const res = await api.post<{
          access: string;
          user: User;
          workspace: Workspace;
        }>("/api/v1/auth/refresh/");
        if (res.access) {
          setAccessToken(res.access);
          if (res.user) setUser(res.user);
          if (res.workspace) setWorkspace(res.workspace);
        }
      } catch {
        // No active session or refresh cookie expired
        setAccessToken(null);
        setUser(null);
        setWorkspace(null);
      } finally {
        setIsLoading(false);
      }
    }
    restoreSession();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.post<{
      access?: string;
      user?: User;
      workspace?: Workspace;
      mfa_required?: boolean;
    }>("/api/v1/auth/login/", { email, password });

    if (res.mfa_required) {
      return { mfa_required: true };
    }

    if (res.access) {
      setAccessToken(res.access);
      if (res.user) setUser(res.user);
      if (res.workspace) setWorkspace(res.workspace);
    }
    return { mfa_required: false };
  };

  const register = async (payload: {
    email: string;
    password: string;
    display_name?: string;
    reporting_currency?: string;
  }) => {
    const res = await api.post<{
      access: string;
      user: User;
      workspace: Workspace;
    }>("/api/v1/auth/register/", payload);

    setAccessToken(res.access);
    setUser(res.user);
    setWorkspace(res.workspace);
  };

  const logout = async () => {
    try {
      await api.post("/api/v1/auth/logout/");
    } catch {
      // ignore
    } finally {
      setAccessToken(null);
      setUser(null);
      setWorkspace(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        workspace,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
