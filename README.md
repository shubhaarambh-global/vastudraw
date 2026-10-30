# Vastudraw

AI-powered residential architecture and floor-plan generation platform with multi-floor planning, intelligent design assistance, deterministic architectural validation, and CAD export.

## Project Overview

Vastudraw is a full-stack architectural AI platform that helps users design residential floor plans with deterministic geometry, Vastu reasoning, and intelligent architectural brain assistance. The system combines:

- **Frontend**: Next.js web application with architectural plan editor, project wizard, generation pages, and review panels.
- **Backend**: FastAPI API service with deterministic generation pipeline, CP-SAT architectural solver, Vastu reasoning engine, and multi-candidate generation.
- **AI Reasoning**: OmniRoute gateway for all LLM-backed AI Architect requests, with deterministic fixtures for testing.
- **Multi-floor Support**: G, G+1, G+2, G+3 configurations with per-floor room assignments and staircase propagation.
- **Deterministic Validation**: All geometry is authoritative, computed in millimetres, and validated through CP-SAT solver and independent validators.
- **CAD Export**: DXF, PDF, SVG, and building-package exporters for production drawing output.

## Core Capabilities

### Architecture
- **AI Topology / Design Intent**: Advisory only — never overrides authoritative geometry.
- **Deterministic Geometry**: Authoritative geometry computed in millimetres by the CP-SAT solver.
- **Architectural Brain**: Concepts applied as non-geometric solver intent; concept size caps must not become hard feasibility caps.
- **Project Revisions**: Immutable and ancestry-aware; every generation creates a new immutable revision.
- **Structural Engineering**: Outside V1 scope (V2 planned).
- **Wet-stack Coordination**: Remains soft (non-authoritative).

### Multi-floor Support
- Supports G (ground only), G+1, G+2, and G+3 configurations.
- Per-floor room assignments validated against `available_floors`.
- Staircases correctly propagate across floors with proper floor preferences.
- Floor-count contract enforced end-to-end from confirmed requirements through generation.

### Vastu Configuration
- **Vastu Enabled**: Vastu-forward planning with soft Vastu scoring.
- **Vastu Disabled**: Maps to practical planning mode; Vastu-aware strategies remain generic, not Vastu-specific.
- **Vastu Strict**: Strict Vastu rules applied through the reasoning profile.

### AI Model Routing
- OmniRoute is the exclusive AI model gateway for the product runtime.
- Every LLM-backed AI Architect request (requirements, design intent, advisory Vastu, architectural brain, revision, plan recognition) goes through `python/ai_vastu/omniroute_http.py`.
- Six `AI_VASTU_*_PROVIDER` selectors accept `omniroute` or `fixture`; every other historical provider selector is retired and fails loudly.
- No direct provider fallback, no Ollama fallback, no deterministic fixture fallback in production runtime.
- Gateway credential is server-side only — never enters browser bundle, logs, or tracked files.

### CAD & Building Package Exports
- DXF export for architectural drawings.
- PDF export for documentation and review.
- SVG export for web preview.
- Building package export for complete deliverable sets.

## Repository Structure

```
vastudraw/
├── apps/
│   ├── api/          # FastAPI backend API (Python)
│   └── web/          # Next.js frontend application
├── docs/             # Project documentation and agent instructions
│   ├── agent-system/ # Agent OS roles and protected contracts
│   ├── agent-memory/ # Knowledge graph and memory system
│   ├── architecture/ # Architecture decision records
│   ├── exec-plans/   # Execution plans for each phase
│   └── runbooks/     # Operational runbooks
├── infra/            # Docker and infrastructure configuration
│   └── docker/
├── packages/         # Shared packages
├── python/
│   └── ai_vastu/     # Core Python AI reasoning and generation engine
│       ├── omniroute_http.py       # OmniRoute gateway client
│       ├── architectural_brain/    # Architectural concept application
│       ├── multi_candidate/        # Multi-candidate generation engine
│       ├── generation/             # Deterministic generation pipeline
│       ├── requirements/           # Requirements intake and confirmation
│       ├── vastu_reasoning/        # Vastu reasoning engine
│       ├── drawing/                # CAD and drawing modules
│       ├── exporting/              # DXF, PDF, SVG exporters
│       └── production/             # Production settings and middleware
├── scripts/          # Development and qualification scripts
├── tests/            # Test suites
│   ├── api/          # API tests
│   ├── auth/         # Authentication tests
│   ├── drawing/      # Drawing tests
│   ├── exporting/    # Export tests
│   ├── production/   # Production qualification tests
│   └── requirements/ # Requirements tests
└── README.md         # This file
```

## Technology Stack

### Frontend
- Next.js (React)
- TypeScript
- Tailwind CSS
- Playwright for e2e browser testing

### Backend
- Python 3.12
- FastAPI
- CP-SAT solver (deterministic architecture)
- Pydantic for data validation
- pytest for testing

### Infrastructure
- Docker containers for API and web
- PostgreSQL / Supabase for production persistence
- GitHub Actions for CI/CD

## Prerequisites

- Python 3.12+
- Node.js 18+ and pnpm
- Docker (optional, for containerized deployment)
- OmniRoute gateway access (for AI Architect runtime requests)

## Local Development Setup

### Backend

```powershell
# Create Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r python/ai_vastu/requirements.txt
pip install -e python/

# Run the API server
python -m uvicorn apps.api.app.main:app --reload
```

### Frontend

```powershell
# Install dependencies
pnpm install

# Run development server
pnpm --filter @ai-vastu/web dev
```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```
APP_ENV=development
NEXT_PUBLIC_AI_VASTU_API_BASE_URL=http://127.0.0.1:8000
AI_VASTU_DATABASE_URL=<your-postgres-url>
AI_VASTU_OMNIROUTE_API_KEY=<server-side-only-gateway-credential>
AI_VASTU_OMNIROUTE_BASE_URL=http://127.0.0.1:20128
```

**Security**: The OmniRoute API key and all secrets must be server-side only. Never commit actual credentials to `.env` — `.env.example` contains only placeholders.

## Running Tests

### Backend Tests

```powershell
# Run all backend tests
pytest

# Run specific test suites
pytest apps/api/tests/
pytest tests/production/
pytest tests/requirements/
```

### Frontend Tests

```powershell
# Run frontend tests
pnpm --filter @ai-vastu/web test

# TypeScript typecheck
pnpm --filter @ai-vastu/web typecheck
```

### Full Validation

```powershell
pnpm validate
```

## Current Experimental Features and Known Limitations

### Multi-floor Generation
G+1, G+2, and G+3 configurations are supported with per-floor room assignments. Staircase propagation across floors has been corrected (Phase 30.3 fix for UUID collision in floor-requirements partitioning).

### Vastu Disabled Mode
Vastu disabled correctly maps to practical planning mode through `influence_mode_for_confirmed()`. Vastu-aware strategies remain generic, not Vastu-specific.

### OmniRoute Gateway
All AI Architect requests route through OmniRoute. Direct provider access is retired. The gateway credential must be supplied through the operator process environment or a secret manager.

### Not V1 Scope
- Structural engineering (V2)
- Production DWG export (requires separate qualified backend)
- Direct provider fallback (retired)

## Security

- No secrets are committed to this repository. `.env.example` contains only placeholders.
- `.env`, `.env.local`, `.env.production` are ignored by `.gitignore`.
- OmniRoute gateway credential is server-side only.
- SQLite databases, logs, and runtime artifacts are excluded from publication.

## License

This repository is published as source-available. A public GitHub repository does not automatically grant others permission to reuse its code. No open-source license is included unless explicitly selected.