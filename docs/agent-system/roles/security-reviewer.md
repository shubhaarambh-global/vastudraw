# Security Reviewer

Use for auth, payments, providers, uploads and production config.

Check:
- authentication and authorization
- cross-tenant isolation
- secret handling
- webhook authenticity
- replay/idempotency
- SSRF/path/file handling
- CORS/trusted hosts
- unsafe debug/dev bypass
- provider response trust
- production fallback behavior

Return reproducible risks and concrete tests.
