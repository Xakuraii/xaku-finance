import React, { useEffect, useRef, useState } from "react";
import { X, KeyRound, Settings2, ExternalLink } from "lucide-react";

interface GoogleCredentialResponse {
  credential?: string;
}

interface GoogleIdApi {
  initialize: (config: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
    auto_select?: boolean;
  }) => void;
  renderButton: (
    parent: HTMLElement,
    options: {
      theme?: "outline" | "filled_blue" | "filled_black";
      size?: "large" | "medium" | "small";
      text?: "signin_with" | "signup_with" | "continue_with" | "signin";
      shape?: "rectangular" | "pill" | "circle" | "square";
      width?: number;
      logo_alignment?: "left" | "center";
    }
  ) => void;
  prompt: () => void;
}

declare global {
  interface Window {
    google?: {
      accounts?: {
        id?: GoogleIdApi;
      };
    };
  }
}

const CLIENT_ID_STORAGE_KEY = "xaku_google_client_id";
const GIS_SCRIPT_ID = "xaku-google-gsi-client";

function readConfiguredClientId(): string {
  const envVal = (import.meta as unknown as { env?: Record<string, string | undefined> }).env
    ?.VITE_GOOGLE_CLIENT_ID;
  if (envVal && envVal.trim()) {
    return envVal.trim();
  }
  try {
    return (localStorage.getItem(CLIENT_ID_STORAGE_KEY) || "").trim();
  } catch {
    return "";
  }
}

export interface GoogleAuthButtonProps {
  onSuccessToken: (idToken: string) => Promise<void> | void;
  label?: string;
  mode?: "signin" | "signup";
  disabled?: boolean;
}

export const GoogleLogo: React.FC<{ className?: string }> = ({ className = "w-4 h-4" }) => (
  <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
    <path
      fill="#4285F4"
      d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z"
    />
    <path
      fill="#34A853"
      d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24Z"
    />
    <path
      fill="#FBBC05"
      d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14Z"
    />
    <path
      fill="#EA4335"
      d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96Z"
    />
  </svg>
);

export const GoogleAuthButton: React.FC<GoogleAuthButtonProps> = ({
  onSuccessToken,
  label = "Continue with Google",
  mode = "signin",
  disabled = false,
}) => {
  const [clientId, setClientId] = useState<string>(readConfiguredClientId);
  const [gisReady, setGisReady] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [draftClientId, setDraftClientId] = useState(clientId);
  const [manualIdToken, setManualIdToken] = useState("");
  const [isSubmittingManual, setIsSubmittingManual] = useState(false);
  const gisContainerRef = useRef<HTMLDivElement | null>(null);
  const callbackRef = useRef(onSuccessToken);

  callbackRef.current = onSuccessToken;

  useEffect(() => {
    if (!clientId) {
      setGisReady(false);
      return;
    }

    const initializeGis = () => {
      const api = window.google?.accounts?.id;
      if (!api || !gisContainerRef.current) return;

      api.initialize({
        client_id: clientId,
        callback: (response: GoogleCredentialResponse) => {
          if (response.credential) {
            void callbackRef.current(response.credential);
          }
        },
      });

      gisContainerRef.current.innerHTML = "";
      const containerWidth = Math.max(260, Math.min(380, gisContainerRef.current.clientWidth || 340));
      api.renderButton(gisContainerRef.current, {
        theme: "outline",
        size: "large",
        text: mode === "signup" ? "signup_with" : "continue_with",
        shape: "rectangular",
        width: containerWidth,
        logo_alignment: "center",
      });
      setGisReady(true);
    };

    if (window.google?.accounts?.id) {
      initializeGis();
      return;
    }

    let script = document.getElementById(GIS_SCRIPT_ID) as HTMLScriptElement | null;
    if (!script) {
      script = document.createElement("script");
      script.id = GIS_SCRIPT_ID;
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }

    script.addEventListener("load", initializeGis);
    return () => {
      script?.removeEventListener("load", initializeGis);
    };
  }, [clientId, mode]);

  const handleSaveClientId = (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = draftClientId.trim();
    try {
      if (cleaned) {
        localStorage.setItem(CLIENT_ID_STORAGE_KEY, cleaned);
      } else {
        localStorage.removeItem(CLIENT_ID_STORAGE_KEY);
      }
    } catch {
      // ignore storage issues
    }
    setClientId(cleaned);
    setConfigModalOpen(false);
  };

  const handleSubmitManualToken = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = manualIdToken.trim();
    if (!trimmed) return;
    setIsSubmittingManual(true);
    try {
      await callbackRef.current(trimmed);
      setConfigModalOpen(false);
      setManualIdToken("");
    } finally {
      setIsSubmittingManual(false);
    }
  };

  return (
    <>
      <div className="space-y-2">
        {clientId ? (
          <div className="space-y-1.5">
            {/* Real Google Identity Services Button */}
            <div
              ref={gisContainerRef}
              className={`w-full flex justify-center min-h-[42px] overflow-hidden rounded-xl ${
                disabled ? "pointer-events-none opacity-50" : ""
              }`}
            />
            {!gisReady && (
              <button
                type="button"
                disabled={disabled}
                onClick={() => window.google?.accounts?.id?.prompt()}
                className="w-full flex items-center justify-center gap-2.5 px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] text-xs font-semibold text-main transition-colors cursor-pointer disabled:opacity-50"
              >
                <GoogleLogo className="w-4 h-4 shrink-0" />
                <span>{label}</span>
              </button>
            )}
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => {
                  setDraftClientId(clientId);
                  setConfigModalOpen(true);
                }}
                className="inline-flex items-center gap-1 text-[10px] text-faint hover:text-muted cursor-pointer"
              >
                <Settings2 className="w-3 h-3" />
                Configure Google Client ID
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            disabled={disabled}
            onClick={() => {
              setDraftClientId(clientId);
              setConfigModalOpen(true);
            }}
            className="w-full flex items-center justify-center gap-2.5 px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] hover:border-[var(--border-strong)] text-xs font-semibold text-main transition-all cursor-pointer disabled:opacity-50 shadow-2xs"
          >
            <GoogleLogo className="w-4 h-4 shrink-0" />
            <span>{label} (Gmail)</span>
          </button>
        )}
      </div>

      {/* Configure Google OAuth Client ID / Direct Token Modal */}
      {configModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
          onClick={() => setConfigModalOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Configure Google Gmail Sign-In"
        >
          <div
            className="w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl space-y-5 text-left"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
              <div className="flex items-center gap-2.5">
                <GoogleLogo className="w-5 h-5 shrink-0" />
                <div>
                  <h3 className="text-sm font-semibold text-main">
                    Google Gmail OAuth Setup
                  </h3>
                  <p className="text-[11px] text-muted">
                    Connect Google Identity Services for 1-click Gmail sign-in
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConfigModalOpen(false)}
                className="text-muted hover:text-main cursor-pointer p-1"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveClientId} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-main mb-1">
                  Google OAuth 2.0 Web Client ID
                </label>
                <p className="text-[11px] text-muted mb-2 leading-relaxed">
                  Paste your <code className="font-mono text-[10px] px-1 py-0.5 rounded bg-[var(--surface-raised)]">*.apps.googleusercontent.com</code> Client ID matching the backend <code className="font-mono text-[10px] px-1 py-0.5 rounded bg-[var(--surface-raised)]">GOOGLE_CLIENT_ID</code> setting (or configure <code className="font-mono text-[10px]">VITE_GOOGLE_CLIENT_ID</code>).
                </p>
                <input
                  type="text"
                  value={draftClientId}
                  onChange={(e) => setDraftClientId(e.target.value)}
                  placeholder="1234567890-abcxyz.apps.googleusercontent.com"
                  className="w-full rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-xs font-mono text-main focus:border-[var(--accent)] focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-between pt-1">
                <a
                  href="https://console.cloud.google.com/apis/credentials"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-gold hover:underline"
                >
                  Google Cloud Console
                  <ExternalLink className="w-3 h-3" />
                </a>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-gold text-xs font-semibold cursor-pointer shadow-xs"
                >
                  Save Client ID
                </button>
              </div>
            </form>

            <div className="border-t border-[var(--border)] pt-4 space-y-2.5">
              <div className="flex items-center gap-1.5 text-xs font-medium text-muted">
                <KeyRound className="w-3.5 h-3.5 text-gold" />
                <span>Or sign in with a verified Google ID Token (JWT)</span>
              </div>
              <form onSubmit={handleSubmitManualToken} className="flex gap-2">
                <input
                  type="text"
                  value={manualIdToken}
                  onChange={(e) => setManualIdToken(e.target.value)}
                  placeholder="Paste Google id_token..."
                  className="flex-1 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-1.5 text-xs font-mono text-main focus:border-[var(--accent)] focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={isSubmittingManual || !manualIdToken.trim()}
                  className="px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] text-xs font-medium text-main cursor-pointer disabled:opacity-40"
                >
                  Verify
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
