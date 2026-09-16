import assert from "node:assert/strict";
import test from "node:test";

import type { ProjectRecord, RevisionRecord } from "../api/client.ts";
import { demoDocument } from "./demo-document.ts";
import {
  loadProjectWorkspace,
  type ProjectWorkspaceApi,
} from "./project-workspace.ts";

function project(currentRevisionId: string | null): ProjectRecord {
  return {
    project_id: demoDocument.project_id,
    name: "Residence",
    created_at: "2026-09-15T00:00:00+00:00",
    current_revision_id: currentRevisionId,
    current_revision_number: currentRevisionId === null ? 0 : 1,
  };
}

function revision(): RevisionRecord {
  return {
    project_id: demoDocument.project_id,
    revision_id: demoDocument.revision_id,
    revision_number: 1,
    parent_revision_id: null,
    created_at: "2026-09-15T00:00:00+00:00",
    document: demoDocument,
    plan_document_hash: "a".repeat(64),
    payload_hash: "b".repeat(64),
  };
}

void test("project workspace returns explicit empty state when no revision exists", async () => {
  let revisionRequested = false;
  const api: ProjectWorkspaceApi = {
    getProject: () => Promise.resolve(project(null)),
    getRevision: () => {
      revisionRequested = true;
      return Promise.resolve(revision());
    },
  };

  const snapshot = await loadProjectWorkspace(api, demoDocument.project_id);

  assert.equal(snapshot.project.current_revision_id, null);
  assert.equal(snapshot.revision, null);
  assert.equal(revisionRequested, false);
});

void test("project workspace hydrates the exact current canonical revision", async () => {
  const expectedRevision = revision();
  const api: ProjectWorkspaceApi = {
    getProject: () => Promise.resolve(project(expectedRevision.revision_id)),
    getRevision: () => Promise.resolve(expectedRevision),
  };

  const snapshot = await loadProjectWorkspace(api, demoDocument.project_id);

  assert.equal(snapshot.revision?.revision_id, expectedRevision.revision_id);
  assert.equal(snapshot.revision.document.project_id, demoDocument.project_id);
  assert.equal(
    snapshot.revision.document.revision_id,
    demoDocument.revision_id,
  );
});

void test("project workspace fails closed on a mismatched revision identity", async () => {
  const expectedRevision = revision();
  const api: ProjectWorkspaceApi = {
    getProject: () => Promise.resolve(project(expectedRevision.revision_id)),
    getRevision: () =>
      Promise.resolve({
        ...expectedRevision,
        revision_id: "99999999-9999-9999-9999-999999999999",
      }),
  };

  await assert.rejects(
    loadProjectWorkspace(api, demoDocument.project_id),
    /Revision identity does not match the project head revision/u,
  );
});
