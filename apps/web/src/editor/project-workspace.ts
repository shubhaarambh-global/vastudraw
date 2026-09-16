import type { ProjectRecord, RevisionRecord } from "../api/client.ts";

export interface ProjectWorkspaceApi {
  getProject: (projectId: string) => Promise<ProjectRecord>;
  getRevision: (
    projectId: string,
    revisionId: string,
  ) => Promise<RevisionRecord>;
}

export interface ProjectWorkspaceSnapshot {
  readonly project: ProjectRecord;
  readonly revision: RevisionRecord | null;
}

export async function loadProjectWorkspace(
  api: ProjectWorkspaceApi,
  projectId: string,
): Promise<ProjectWorkspaceSnapshot> {
  const normalizedProjectId = projectId.trim();
  if (normalizedProjectId.length === 0) {
    throw new TypeError("Project ID must not be empty.");
  }

  const project = await api.getProject(normalizedProjectId);
  if (project.project_id !== normalizedProjectId) {
    throw new Error(
      "Project response identity does not match the requested project.",
    );
  }

  if (project.current_revision_id === null) {
    return { project, revision: null };
  }

  const revision = await api.getRevision(
    project.project_id,
    project.current_revision_id,
  );
  if (revision.project_id !== project.project_id) {
    throw new Error("Revision project identity does not match its project.");
  }
  if (revision.revision_id !== project.current_revision_id) {
    throw new Error(
      "Revision identity does not match the project head revision.",
    );
  }
  if (revision.document.project_id !== project.project_id) {
    throw new Error(
      "PlanDocument project identity does not match its project.",
    );
  }
  if (revision.document.revision_id !== revision.revision_id) {
    throw new Error(
      "PlanDocument revision identity does not match the loaded revision.",
    );
  }

  return { project, revision };
}
