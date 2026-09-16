"use client";

import { useEffect, useState } from "react";

interface CreateProjectDialogProps {
  readonly open: boolean;
  readonly busy: boolean;
  readonly onClose: () => void;
  readonly onCreate: (name: string) => Promise<void>;
}

export function CreateProjectDialog({
  open,
  busy,
  onClose,
  onCreate,
}: CreateProjectDialogProps) {
  const [name, setName] = useState("New residence");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setName("New residence");
      setError(null);
    }
  }, [open]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="saas-dialog-backdrop"
      role="presentation"
      onMouseDown={onClose}
    >
      <section
        className="saas-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-project-title"
        onMouseDown={(event) => {
          event.stopPropagation();
        }}
      >
        <div className="saas-dialog-heading">
          <div>
            <p className="saas-kicker">New project</p>
            <h2 id="create-project-title">Create a planning workspace</h2>
          </div>
          <button
            className="saas-icon-button"
            type="button"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <p className="saas-muted">
          Geometry is not invented at creation time. The project starts empty
          until an explicit canonical PlanDocument revision is created.
        </p>
        <label className="saas-field">
          <span>Project name</span>
          <input
            value={name}
            onChange={(event) => {
              setName(event.target.value);
            }}
            autoFocus
          />
        </label>
        {error === null ? null : <p className="saas-error-text">{error}</p>}
        <div className="saas-dialog-actions">
          <button type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            className="saas-button-primary"
            type="button"
            disabled={busy || name.trim().length === 0}
            onClick={() => {
              void onCreate(name)
                .then(() => {
                  onClose();
                })
                .catch((caught: unknown) => {
                  setError(
                    caught instanceof Error
                      ? caught.message
                      : "Project creation failed.",
                  );
                });
            }}
          >
            {busy ? "Creating…" : "Create project"}
          </button>
        </div>
      </section>
    </div>
  );
}
