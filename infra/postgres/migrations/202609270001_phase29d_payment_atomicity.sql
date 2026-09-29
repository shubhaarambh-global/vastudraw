BEGIN;

CREATE TABLE IF NOT EXISTS public.billing_payment_orders (
    provider text NOT NULL,
    merchant_order_id text NOT NULL,
    user_id uuid NOT NULL,
    sku text NOT NULL,
    amount_paise integer NOT NULL CHECK (amount_paise > 0),
    currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    idempotency_key text NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (
        status IN (
            'pending',
            'checkout_created',
            'checkout_unknown',
            'checkout_failed',
            'fulfilled'
        )
    ),
    provider_order_id text,
    checkout_url text,
    expires_at timestamptz,
    failure_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    fulfilled_at timestamptz,
    PRIMARY KEY (provider, merchant_order_id),
    UNIQUE (provider, user_id, idempotency_key)
);

CREATE UNIQUE INDEX IF NOT EXISTS billing_payment_orders_provider_order_idx
    ON public.billing_payment_orders(provider, provider_order_id)
    WHERE provider_order_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS billing_payment_orders_reconciliation_idx
    ON public.billing_payment_orders(provider, status, created_at, merchant_order_id);

ALTER TABLE public.billing_events
    ADD COLUMN IF NOT EXISTS merchant_order_id text,
    ADD COLUMN IF NOT EXISTS user_id uuid,
    ADD COLUMN IF NOT EXISTS sku text;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'billing_events_payment_order_fk'
          AND conrelid = 'public.billing_events'::regclass
    ) THEN
        ALTER TABLE public.billing_events
            ADD CONSTRAINT billing_events_payment_order_fk
            FOREIGN KEY (provider, merchant_order_id)
            REFERENCES public.billing_payment_orders(provider, merchant_order_id);
    END IF;
END
$$;

ALTER TABLE public.billing_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_project_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_payment_orders ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.billing_accounts FROM PUBLIC;
REVOKE ALL ON TABLE public.billing_project_grants FROM PUBLIC;
REVOKE ALL ON TABLE public.billing_events FROM PUBLIC;
REVOKE ALL ON TABLE public.billing_payment_orders FROM PUBLIC;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON TABLE public.billing_accounts FROM anon;
        REVOKE ALL ON TABLE public.billing_project_grants FROM anon;
        REVOKE ALL ON TABLE public.billing_events FROM anon;
        REVOKE ALL ON TABLE public.billing_payment_orders FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON TABLE public.billing_accounts FROM authenticated;
        REVOKE ALL ON TABLE public.billing_project_grants FROM authenticated;
        REVOKE ALL ON TABLE public.billing_events FROM authenticated;
        REVOKE ALL ON TABLE public.billing_payment_orders FROM authenticated;
    END IF;
END
$$;

COMMIT;
