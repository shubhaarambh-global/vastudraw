"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export type BrowserAuthMode = "supabase" | "development" | "unconfigured";

let cachedClient: SupabaseClient | null = null;

export function browserAuthMode(): BrowserAuthMode {
  const configuredMode =
    process.env.NEXT_PUBLIC_AI_VASTU_AUTH_MODE?.trim().toLowerCase();
  const devToken = process.env.NEXT_PUBLIC_AI_VASTU_DEV_BEARER_TOKEN?.trim();
  if (
    configuredMode === "development" &&
    devToken &&
    process.env.NODE_ENV !== "production"
  ) {
    return "development";
  }
  if (
    process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() &&
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim()
  ) {
    return "supabase";
  }
  return "unconfigured";
}

export function authConfigurationAvailable(): boolean {
  return browserAuthMode() !== "unconfigured";
}

export function browserSupabaseClient(): SupabaseClient {
  if (cachedClient !== null) {
    return cachedClient;
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const publishableKey =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim();

  if (!url || !publishableKey) {
    throw new Error(
      "Supabase Auth is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.",
    );
  }

  cachedClient = createClient(url, publishableKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  });
  return cachedClient;
}

export async function browserAccessToken(): Promise<string | null> {
  const mode = browserAuthMode();
  if (mode === "development") {
    return process.env.NEXT_PUBLIC_AI_VASTU_DEV_BEARER_TOKEN?.trim() ?? null;
  }
  if (mode !== "supabase") {
    return null;
  }
  const { data, error } = await browserSupabaseClient().auth.getSession();
  if (error) {
    throw error;
  }
  return data.session?.access_token ?? null;
}
