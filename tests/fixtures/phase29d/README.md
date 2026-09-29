# Phase 29D payment fixtures

These payloads are synthetic, deterministic, and credential-free. They model the
smallest PhonePe Standard Checkout and persisted-order cases needed to exercise
provider parsing, failure classification, replay handling, transaction rollback,
concurrency, and provider namespace isolation.

`fixture-oauth-token` is a non-secret test sentinel and must never be accepted as
a production credential.
