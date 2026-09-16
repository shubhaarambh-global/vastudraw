# ADR-014 — Canonical JSON and Content Hash

Status: Accepted in Phase 1

## Decision

Use deterministic UTF-8 JSON serialization with sorted object keys and compact separators, then SHA-256 the document while excluding the `content_hash` field itself.

## Rationale

This gives stable revision integrity checks and supports reproducibility tests without making transport formatting authoritative.
