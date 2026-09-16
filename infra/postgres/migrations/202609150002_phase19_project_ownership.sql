BEGIN;

CREATE TABLE IF NOT EXISTS public.ai_vastu_project_owners (
    project_id UUID PRIMARY KEY,
    owner_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ai_vastu_project_owner_project_fk
        FOREIGN KEY (project_id)
        REFERENCES public.ai_vastu_projects(project_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ai_vastu_project_owners_user_idx
    ON public.ai_vastu_project_owners(owner_user_id, project_id);

ALTER TABLE public.ai_vastu_project_owners ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.ai_vastu_project_owners FROM PUBLIC;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'anon'
    ) THEN
        EXECUTE
            'REVOKE ALL ON TABLE public.ai_vastu_project_owners FROM anon';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'authenticated'
    ) THEN
        EXECUTE
            'REVOKE ALL ON TABLE public.ai_vastu_project_owners FROM authenticated';
    END IF;
END
$$;

COMMIT;
