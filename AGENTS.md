# Vastudraw Codex Map

Vastudraw is an already-qualified production system. Inspect first; preserve qualified behavior; make narrow, test-backed changes.

## Baselines
- Frozen V1: `phase2d9k-v1-qualified` -> `17bd86da29c50c8f73b8a47f5a4c186cf2bd7c26`
- Qualified post-V1: `post-v1-development-qualified` -> `cbd295f5e9028186acbfb14f40c1142e3a003b27`
- Active launch-hardening branch: `phase29`

## Read before architecture-sensitive work
- `docs/agent-system/protected-contracts.md`
- `docs/agent-system/orchestration-protocol.md`
- `docs/agent-memory/README.md`
- `docs/agent-memory/knowledge-graph.json`

## Core invariants
- Deterministic geometry/validators are authoritative.
- AI topology/sizing/design intent is advisory.
- Architectural-brain maximum areas must not become new hard feasibility caps.
- Wet-stack coordination remains SOFT.
- Frozen Vastu rules/hashes are protected.
- Canonical geometry remains millimetres.
- Project revisions remain immutable/ancestry-aware.
- Structural engineering remains outside V1.
- PhonePe is the launch payment direction; Razorpay stays optional/future.
- The Phase 29 local-development AI default is `ollama_local` with the qualified
  Qwen3-VL pin. APINEX is optional, explicit, development-only, and not qualified.
- NVIDIA NIM remains the separately configured hosted staging/production-shaped
  profile; production entitlement is still blocked. No hosted/production profile
  may silently fall back to Ollama or APINEX.
- OpenRouter and direct Gemini are retained legacy/inactive adapters.
- Dev billing bypass must never work in production.

## Git safety
Never use `git add .`, `git reset --hard`, `git clean -fd`, force push, or destructive broad checkout/restore.
Stage exact files only. Do not delete known local archives/payloads/backups.

## Validation
Run focused checks first, then subsystem checks, then `git diff --check`, then `pnpm validate`.
Never claim a live service passed unless it was actually exercised.

## Model routing
Before substantial delegation, use the `vastudraw-model-router` skill.
GPT-5.6 Sol Medium is the default and required model/effort for every Vastudraw
Agent OS role, skill, and agentic development task. A different model or
reasoning effort requires explicit user approval; difficulty, security,
architecture, release, payment, and authentication risk do not authorize an
automatic change. If GPT-5.6 Sol Medium is temporarily unavailable, pause and
retry it unless the user explicitly approves another profile.

The Model Router routes roles, sequencing/parallelism, context and skills,
tests/reviewers, and human-review escalation. It does not automatically route
work to a different model or reasoning effort. When Medium is insufficient,
use independent agents, adversarial or guardian review, more evidence, and
smaller tasks before escalating the decision to the user.
Model routing applies to development agents, not the Vastudraw product runtime providers.

## Agent operating model
For substantial tasks use the `vastudraw-orchestrator` skill.
The coordinator owns the final plan, integration, Git and release claims.
Specialists return evidence/findings/patches; they do not independently redefine product rules.
Use worktrees or disjoint scopes for parallel writers.

## Skills
- `vastudraw-model-router`
- `vastudraw-orchestrator`
- `vastudraw-memory-graph`
- `vastudraw-planning`
- `vastudraw-implementation`
- `vastudraw-fixtures`
- `vastudraw-testing`
- `vastudraw-qa`
- `vastudraw-architecture-guardian`
- `vastudraw-production-launch`
- `vastudraw-release`

Detailed role cards live under `docs/agent-system/roles/`.
