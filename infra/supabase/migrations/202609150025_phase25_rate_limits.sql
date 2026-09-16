-- Phase 25: durable application rate-limit windows.
-- Server-only table: no client role receives privileges.

CREATE TABLE IF NOT EXISTS public.ai_vastu_rate_limit_windows (
    scope text NOT NULL,
    key_hash text NOT NULL,
    window_start timestamptz NOT NULL,
    request_count integer NOT NULL CHECK (request_count > 0),
    PRIMARY KEY (scope, key_hash, window_start)
);

REVOKE ALL ON TABLE public.ai_vastu_rate_limit_windows FROM anon;
REVOKE ALL ON TABLE public.ai_vastu_rate_limit_windows FROM authenticated;

ALTER TABLE public.ai_vastu_rate_limit_windows ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS ai_vastu_rate_limit_windows_window_start_idx
    ON public.ai_vastu_rate_limit_windows (window_start);

COMMENT ON TABLE public.ai_vastu_rate_limit_windows IS
    'Server-side fixed-window counters for expensive production API operations.';
