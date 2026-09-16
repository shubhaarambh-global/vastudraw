BEGIN;

CREATE TABLE IF NOT EXISTS public.ai_vastu_projects (
    project_id UUID PRIMARY KEY,
    name TEXT NOT NULL CHECK (char_length(btrim(name)) BETWEEN 1 AND 200),
    created_at TIMESTAMPTZ NOT NULL,
    current_revision_id UUID NULL,
    current_revision_number BIGINT NOT NULL DEFAULT 0
        CHECK (current_revision_number >= 0),
    CHECK (
        (current_revision_number = 0 AND current_revision_id IS NULL)
        OR
        (current_revision_number > 0 AND current_revision_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS public.ai_vastu_project_revisions (
    project_id UUID NOT NULL,
    revision_id UUID NOT NULL,
    revision_number BIGINT NOT NULL CHECK (revision_number > 0),
    parent_revision_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL,
    plan_document JSONB NOT NULL CHECK (jsonb_typeof(plan_document) = 'object'),
    plan_document_hash CHAR(64) NOT NULL
        CHECK (plan_document_hash ~ '^[0-9a-f]{64}$'),
    source_candidate_id UUID NULL,
    note TEXT NULL CHECK (note IS NULL OR char_length(note) <= 2000),
    generated_outputs JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(generated_outputs) = 'array'),
    payload_hash CHAR(64) NOT NULL CHECK (payload_hash ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (project_id, revision_id),
    UNIQUE (project_id, revision_number),
    CONSTRAINT ai_vastu_revision_project_fk
        FOREIGN KEY (project_id)
        REFERENCES public.ai_vastu_projects(project_id)
        ON DELETE RESTRICT,
    CONSTRAINT ai_vastu_revision_parent_fk
        FOREIGN KEY (project_id, parent_revision_id)
        REFERENCES public.ai_vastu_project_revisions(project_id, revision_id)
        DEFERRABLE INITIALLY DEFERRED
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ai_vastu_project_current_revision_fk'
    ) THEN
        ALTER TABLE public.ai_vastu_projects
        ADD CONSTRAINT ai_vastu_project_current_revision_fk
            FOREIGN KEY (project_id, current_revision_id)
            REFERENCES public.ai_vastu_project_revisions(project_id, revision_id)
            DEFERRABLE INITIALLY DEFERRED;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS ai_vastu_project_revisions_project_created_idx
    ON public.ai_vastu_project_revisions(project_id, created_at);

COMMIT;
