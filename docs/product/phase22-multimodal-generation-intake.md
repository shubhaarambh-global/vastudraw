# Phase 22 — Multimodal generation intake

Phase 22 introduces a project-scoped client brief for generation.

Supported reference inputs:

- UTF-8 text prompt, maximum 12,000 characters.
- JPEG images.
- PNG images.
- PDF documents.
- At most eight attachments, 20 MiB per file, 50 MiB combined.

The API validates the declared media type against the file signature and stores files under
server-generated names. Every attachment has a SHA-256 digest and every intake has an integrity
hash. Access is project-owner authenticated.

## Authority boundary

Uploaded prompts, images, and PDFs are **reference inputs only**. They do not become canonical
plot geometry, room dimensions, walls, openings, or PlanDocument entities. Phase 23 is expected to
interpret these references into a structured draft that the user must confirm before deterministic
architectural generation can consume it.

Production deployments must configure `AI_VASTU_GENERATION_UPLOAD_ROOT` as an absolute path on a
persistent volume. The application fails closed in production when that storage root is missing.
