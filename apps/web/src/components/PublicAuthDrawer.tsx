"use client";

import { useEffect, useState } from "react";

import { browserAuthMode, browserSupabaseClient } from "../auth/browser.ts";

type AuthMode = "sign-in" | "sign-up";

type PublicAuthDrawerProps = {
  readonly open: boolean;
  readonly initialMode: AuthMode;
  readonly onClose: () => void;
  readonly onAuthenticated: () => void;
};

export function PublicAuthDrawer({
  open,
  initialMode,
  onClose,
  onAuthenticated,
}: PublicAuthDrawerProps) {
  const workspaceAuthMode = browserAuthMode();
  const isDevelopment = workspaceAuthMode === "development";

  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (open) {
      setMode(initialMode);
      setStatus("");
    }
  }, [initialMode, open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.classList.add("public-auth-open");

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.classList.remove("public-auth-open");
    };
  }, [onClose, open]);

  const submit = async () => {
    setBusy(true);
    setStatus("");

    try {
      const client = browserSupabaseClient();

      const result =
        mode === "sign-in"
          ? await client.auth.signInWithPassword({
              email,
              password,
            })
          : await client.auth.signUp({
              email,
              password,
            });

      if (result.error) {
        throw result.error;
      }

      if (mode === "sign-in") {
        onAuthenticated();
        return;
      }

      if (result.data.session) {
        onAuthenticated();
        return;
      }

      setStatus(
        "Account created. Check your email to confirm your account, then log in.",
      );
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Authentication failed.",
      );
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return null;
  }

  return (
    <div
      className="public-auth-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <aside
        className="public-auth-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="public-auth-title"
      >
        <div className="public-auth-drawer-header">
          <div>
            <p className="saas-kicker">
              {isDevelopment ? "Development workspace" : "Secure workspace"}
            </p>

            <h2 id="public-auth-title">
              {isDevelopment
                ? "Continue locally"
                : mode === "sign-in"
                  ? "Welcome back"
                  : "Create your account"}
            </h2>
          </div>

          <button
            type="button"
            className="public-auth-close"
            aria-label="Close authentication"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        {isDevelopment ? (
          <>
            <p className="public-auth-intro">
              Development authentication is active. No credentials are required
              while testing Vastudraw locally.
            </p>

            <section className="public-auth-dev-card">
              <div>
                <strong>Local developer workspace</strong>
                <span>
                  Projects, generation, editor and exports use the local
                  development identity.
                </span>
              </div>

              <button
                type="button"
                onClick={() => {
                  onAuthenticated();
                }}
              >
                Continue as local developer
              </button>
            </section>

            <p className="public-auth-dev-note">
              Real login and account creation will activate automatically when
              Supabase authentication is configured for production.
            </p>
          </>
        ) : (
          <>
            <p className="public-auth-intro">
              {mode === "sign-in"
                ? "Sign in to continue your projects and generated plans."
                : "Create your workspace to save projects, revisions and exports."}
            </p>

            <div className="public-auth-tabs" role="tablist">
              <button
                type="button"
                className={mode === "sign-in" ? "is-active" : ""}
                onClick={() => {
                  setMode("sign-in");
                  setStatus("");
                }}
              >
                Log in
              </button>

              <button
                type="button"
                className={mode === "sign-up" ? "is-active" : ""}
                onClick={() => {
                  setMode("sign-up");
                  setStatus("");
                }}
              >
                Sign up
              </button>
            </div>

            <div className="public-auth-form">
              <label>
                <span>Email address</span>
                <input
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value);
                  }}
                />
              </label>

              <label>
                <span>Password</span>
                <input
                  type="password"
                  autoComplete={
                    mode === "sign-in" ? "current-password" : "new-password"
                  }
                  placeholder="Minimum 6 characters"
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      void submit();
                    }
                  }}
                />
              </label>

              <button
                type="button"
                className="public-auth-submit"
                disabled={
                  busy || email.trim().length === 0 || password.length < 6
                }
                onClick={() => {
                  void submit();
                }}
              >
                {busy
                  ? "Please wait…"
                  : mode === "sign-in"
                    ? "Log in"
                    : "Create account"}
              </button>

              {status ? <p className="public-auth-status">{status}</p> : null}
            </div>
          </>
        )}

        <div className="public-auth-trust">
          <span>Secure authentication</span>
          <span>•</span>
          <span>Private project workspace</span>
        </div>
      </aside>
    </div>
  );
}
