"use client";

import type { Session } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  configuredApiBaseUrl,
  ProjectApiClient,
  type ProjectRecord,
} from "../../api/client.ts";
import {
  browserAccessToken,
  browserAuthMode,
  browserSupabaseClient,
} from "../../auth/browser.ts";

export interface WorkspaceProjectsState {
  readonly mode: ReturnType<typeof browserAuthMode>;
  readonly authReady: boolean;
  readonly authenticated: boolean;
  readonly userLabel: string;
  readonly projects: readonly ProjectRecord[];
  readonly status: string;
  readonly busy: boolean;
  readonly refreshProjects: () => Promise<void>;
  readonly createProject: (name: string) => Promise<ProjectRecord>;
  readonly signOut: () => Promise<void>;
}

export function useWorkspaceProjects(): WorkspaceProjectsState {
  const mode = browserAuthMode();
  const [session, setSession] = useState<Session | null>(null);
  const [authReady, setAuthReady] = useState(mode !== "supabase");
  const [projects, setProjects] = useState<readonly ProjectRecord[]>([]);
  const [status, setStatus] = useState("Workspace ready");
  const [busy, setBusy] = useState(false);

  const api = useMemo(
    () =>
      new ProjectApiClient(configuredApiBaseUrl(), fetch, browserAccessToken),
    [],
  );

  useEffect(() => {
    if (mode !== "supabase") {
      setAuthReady(true);
      return;
    }

    const supabase = browserSupabaseClient();
    void supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setAuthReady(true);
    });

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setAuthReady(true);
    });

    return () => {
      data.subscription.unsubscribe();
    };
  }, [mode]);

  const authenticated = mode === "development" || session !== null;

  const refreshProjects = useCallback(async () => {
    setBusy(true);
    try {
      const listed = await api.listProjects();
      setProjects(listed);
      setStatus(
        listed.length === 0
          ? "No projects yet"
          : `${String(listed.length)} projects loaded`,
      );
    } finally {
      setBusy(false);
    }
  }, [api]);

  useEffect(() => {
    if (!authenticated) {
      setProjects([]);
      return;
    }

    void refreshProjects().catch((error: unknown) => {
      setStatus(
        error instanceof Error ? error.message : "Could not load projects.",
      );
    });
  }, [authenticated, refreshProjects]);

  const createProject = useCallback(
    async (name: string) => {
      const normalized = name.trim();
      if (normalized.length === 0) {
        throw new TypeError("Project name must not be empty.");
      }

      setBusy(true);
      try {
        const project = await api.createProject(
          normalized,
          crypto.randomUUID(),
        );
        const listed = await api.listProjects();
        setProjects(listed);
        setStatus(`Created ${project.name}`);
        return project;
      } finally {
        setBusy(false);
      }
    },
    [api],
  );

  const signOut = useCallback(async () => {
    if (mode !== "supabase") {
      return;
    }
    await browserSupabaseClient().auth.signOut();
  }, [mode]);

  const userLabel =
    mode === "development"
      ? "Local developer"
      : (session?.user.email ?? session?.user.id ?? "Authenticated user");

  return {
    mode,
    authReady,
    authenticated,
    userLabel,
    projects,
    status,
    busy,
    refreshProjects,
    createProject,
    signOut,
  };
}
