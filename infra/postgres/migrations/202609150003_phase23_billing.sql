BEGIN;

CREATE TABLE IF NOT EXISTS billing_accounts (
    user_id uuid PRIMARY KEY,
    free_generation_available boolean NOT NULL DEFAULT true,
    project_credits integer NOT NULL DEFAULT 0 CHECK (project_credits >= 0),
    active_subscription_sku text,
    subscription_status text NOT NULL DEFAULT 'none',
    subscription_period_end timestamptz,
    provider_subscription_id text
);

CREATE TABLE IF NOT EXISTS billing_project_grants (
    user_id uuid NOT NULL,
    project_id uuid NOT NULL,
    source text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, project_id)
);

CREATE INDEX IF NOT EXISTS billing_project_grants_user_idx
    ON billing_project_grants(user_id);

CREATE TABLE IF NOT EXISTS billing_events (
    provider text NOT NULL,
    event_key text NOT NULL,
    event_type text NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, event_key)
);

COMMIT;
