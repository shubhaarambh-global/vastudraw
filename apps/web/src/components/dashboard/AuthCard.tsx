"use client";

import { useState } from "react";

import { browserSupabaseClient } from "../../auth/browser.ts";

export function AuthCard() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("Sign in to access your projects.");
  const [busy, setBusy] = useState(false);

  const submit = async (mode: "sign-in" | "sign-up") => {
    setBusy(true);
    try {
      const client = browserSupabaseClient();
      const result =
        mode === "sign-in"
          ? await client.auth.signInWithPassword({ email, password })
          : await client.auth.signUp({ email, password });
      if (result.error) {
        throw result.error;
      }
      setStatus(
        mode === "sign-in"
          ? "Signed in. Loading your dashboard…"
          : "Account created. Check your email if confirmation is enabled.",
      );
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Authentication failed.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="auth-card">
      <p className="eyebrow">Secure workspace</p>
      <h2>Sign in to AI Vastu Architect</h2>
      <p className="dashboard-muted">
        Projects are isolated by authenticated user ownership.
      </p>
      <label>
        Email
        <input
          autoComplete="email"
          type="email"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
          }}
        />
      </label>
      <label>
        Password
        <input
          autoComplete="current-password"
          type="password"
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />
      </label>
      <div className="dashboard-actions">
        <button
          className="primary-action"
          type="button"
          disabled={busy || email.trim().length === 0 || password.length < 6}
          onClick={() => {
            void submit("sign-in");
          }}
        >
          Sign in
        </button>
        <button
          type="button"
          disabled={busy || email.trim().length === 0 || password.length < 6}
          onClick={() => {
            void submit("sign-up");
          }}
        >
          Create account
        </button>
      </div>
      <p className="dashboard-status">{status}</p>
    </section>
  );
}
