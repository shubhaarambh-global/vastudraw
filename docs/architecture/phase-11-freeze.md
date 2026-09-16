# Phase 11 freeze — API, immutable revisions and persistence boundary

Phase 11 scope:

- immutable project revision models;
- repository protocol;
- transactional SQLite reference adapter;
- optimistic concurrency on revision append;
- canonical PlanDocument hash preservation;
- revision payload hashes;
- save/load API endpoints;
- durable reopen smoke test;
- API and persistence tests.

Out of scope and unchanged:

- solver behavior;
- geometry construction;
- Vastu rule content;
- validation/scoring algorithms;
- authentication/authorization;
- production PostgreSQL/Supabase adapter;
- object-storage implementation;
- interactive editor;
- exporters.
