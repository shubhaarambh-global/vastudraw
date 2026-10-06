"""Repeatable Phase 29F loopback acceptance; never manages operator processes.

Run through scripts/run-project-python.mjs with the Phase 29F development
environment loaded. Evidence contains structural results, never model text.
API generation responses are retained locally for exact candidate selection.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "6a7d5150-8bd5-4e09-8bb5-109dac7132ec"
DRAFT = "28bc29d8-4ad0-4303-98db-1dc37cc2f306"
MODEL = "qwen3-vl:8b-instruct-q4_K_M"
EVIDENCE = ROOT / ".local/phase29f-evidence"


class AcceptanceFailure(RuntimeError):
    """Sanitized harness failure whose message contains no provider/client text."""


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AcceptanceFailure(label)


def guard_environment() -> None:
    require(os.getenv("APP_ENV") == "development", "Development environment required")
    for selector in (
        "REQUIREMENTS",
        "ARCHITECT",
        "VASTU",
        "ARCHITECTURAL_BRAIN",
        "REVISION",
        "PLAN_RECOGNITION",
    ):
        require(
            os.getenv(f"AI_VASTU_{selector}_PROVIDER") == "ollama_local",
            f"{selector} must explicitly select ollama_local",
        )
    require(os.getenv("AI_VASTU_OLLAMA_MODEL") == MODEL, "Exact model pin required")
    require(
        os.getenv("AI_VASTU_OLLAMA_BASE_URL") == "http://127.0.0.1:11434",
        "Only canonical loopback Ollama endpoint allowed",
    )
    require(os.getenv("AI_VASTU_PAYMENT_GATEWAY") == "disabled", "Payments must be disabled")
    require(os.getenv("AI_VASTU_AUTH_MODE") == "development", "Development auth required")
    require(not os.getenv("AI_VASTU_DATABASE_URL", "").strip(), "No hosted database configured")
    for variable, expected in (
        ("AI_VASTU_SQLITE_PATH", "phase29f-projects.sqlite3"),
        ("AI_VASTU_BILLING_SQLITE_PATH", "phase29f-billing.sqlite3"),
        ("AI_VASTU_REQUIREMENTS_PATH", "phase29f-requirements"),
    ):
        configured = Path(os.getenv(variable, ""))
        require(configured.name == expected, f"Persistent Phase 29F {variable} required")


class Acceptance:
    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []
        self.client = httpx.Client(
            base_url="http://127.0.0.1:8000",
            trust_env=False,
            headers={"Authorization": f"Bearer {os.environ['AI_VASTU_DEV_BEARER_TOKEN']}"},
            timeout=httpx.Timeout(1800, connect=3),
            follow_redirects=False,
        )

    def record(self, step: str, **details: Any) -> None:
        result = {"step": step, "status": "PASS", **details}
        self.results.append(result)
        print(json.dumps(result, sort_keys=True), flush=True)

    def request(self, method: str, path: str, expected: int = 200, **kwargs: Any) -> httpx.Response:
        require(path.startswith("/") and not path.startswith("//"), "Only relative API paths")
        response = self.client.request(method, path, **kwargs)
        require(response.status_code == expected, f"{method} {path}: HTTP {response.status_code}")
        return response

    def vastu(self) -> None:
        from ai_vastu.requirements.store import RequirementsStore
        from ai_vastu.vastu_reasoning.catalog import load_soft_vastu_catalog
        from ai_vastu.vastu_reasoning.service import create_vastu_reasoning_service

        store = RequirementsStore.from_environment()
        confirmed = store.get_confirmed(UUID(DRAFT))
        draft = store.get_draft(UUID(DRAFT))
        catalog = load_soft_vastu_catalog()
        rules_by_id = {rule.rule_id: rule for rule in catalog.rules}
        for index in range(1, 4):
            profile = create_vastu_reasoning_service().reason(
                confirmed=confirmed,
                original_prompt=draft.prompt,
            )
            require(profile.provider == "ollama_local" and profile.model == MODEL, "Provenance")
            require(profile.content_hash == profile.compute_content_hash(), "Content hash")
            require(len(profile.rules) == len(rules_by_id), "Expected rule count")
            require({rule.rule_id for rule in profile.rules} == set(rules_by_id), "Exact rule set")
            for item in profile.rules:
                rule = rules_by_id[item.rule_id]
                require(item.importance in rule.allowed_importance, "Importance policy")
                require(item.flexibility in rule.allowed_flexibility, "Flexibility policy")
                if not rule.reasoning_adjustable:
                    require(item.weight_multiplier_basis_points == 10000, "Fixed rule weight")
            self.record(
                f"RUN_{index}",
                provider=profile.provider,
                model=profile.model,
                rules=len(profile.rules),
                unknown_rules=0,
                policy_violations=0,
                hash_valid=True,
                normalization=True,
            )

    def basic(self) -> None:
        self.request("GET", "/health")
        response = self.request(
            "OPTIONS",
            "/projects",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        require(
            response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000",
            "Loopback frontend CORS",
        )
        self.request("GET", "/projects", expected=401, headers={"Authorization": "Bearer invalid"})
        project = self.request("GET", f"/projects/{PROJECT}").json()
        require(project["project_id"] == PROJECT, "Existing project identity")
        self.request("GET", f"/requirements/drafts/{DRAFT}/confirmed")
        self.record("health-cors-auth-project-confirmed", http_status=200, invalid_auth_status=401)

    def generation(self) -> None:
        from ai_vastu.multi_candidate.models import CandidateRunResult

        self.request("GET", f"/projects/{PROJECT}")
        self.request("GET", f"/requirements/drafts/{DRAFT}/confirmed")
        response = self.request(
            "POST",
            f"/confirmed-generation/projects/{PROJECT}/alternatives",
            json={"draft_id": DRAFT, "accept_profile_defaults": True, "max_alternatives": 4},
        )
        payload = response.json()
        run = CandidateRunResult.model_validate_json(json.dumps(payload["candidate_run"]))
        require(payload["billing_reason"] == "development_bypass", "Generation development bypass")
        require(payload["quota_consumed"] is False, "Preview must not consume quota")
        require(all(item.valid_architecture for item in run.candidates), "Deterministic validity")
        require(run.content_hash == run.compute_content_hash(), "Candidate run hash")
        # Private local canonical candidate evidence, never printed to stdout.
        candidate_path = EVIDENCE / f"candidate-run-{run.content_hash}.json"
        if not candidate_path.exists():
            candidate_path.write_text(run.model_dump_json(), encoding="utf-8")
        self.record(
            "confirmed-generation",
            alternatives=len(run.candidates),
            run_hash_valid=True,
            revision_persisted=payload["revision_persisted"],
            quota_consumed=payload["quota_consumed"],
            billing_reason=payload["billing_reason"],
        )

    def remainder(self) -> None:
        from ai_vastu.multi_candidate.models import CandidateRunResult
        from ai_vastu.plan_schema import PlanDocument
        from ai_vastu.projects.models import RevisionRecord

        candidate_path = max(
            EVIDENCE.glob("candidate-run-*.json"), key=lambda path: path.stat().st_mtime
        )
        run = CandidateRunResult.model_validate_json(candidate_path.read_text())
        candidate = next(item for item in run.candidates if item.plan_document is not None)
        billing_before = self.request("GET", "/billing/me").json()
        selected = self.request(
            "POST",
            f"/confirmed-generation/projects/{PROJECT}/alternatives/select",
            json={
                "draft_id": DRAFT,
                "candidate_run_hash": run.content_hash,
                "candidate_id": str(candidate.candidate_id),
                "plan_document": candidate.plan_document.model_dump(mode="json")
                if candidate.plan_document is not None
                else None,
            },
        ).json()
        revision_id = selected["revision_id"]
        project = self.request("GET", f"/projects/{PROJECT}").json()
        require(
            selected["billing_reason"] in {"development_bypass", "already_persisted"},
            "Selection development bypass or idempotent replay",
        )
        require(
            self.request("GET", "/billing/me").json() == billing_before,
            "Selection bypass must preserve actual billing quota",
        )
        if selected["billing_reason"] != "already_persisted":
            require(project["current_revision_id"] == revision_id, "Selected revision persisted")
        parent_revision_id = project["current_revision_id"]
        original = RevisionRecord.model_validate_json(
            self.request("GET", f"/projects/{PROJECT}/revisions/{revision_id}").text
        )
        self.record(
            "select-save-reopen",
            revision=revision_id,
            hash_valid=original.plan_document_hash == original.document.compute_content_hash(),
        )
        # Save a new exact canonical revision without altering geometry.
        document = (
            PlanDocument.model_validate(original.document.model_dump())
            .model_copy(update={"revision_id": uuid4(), "content_hash": None})
            .with_content_hash()
        )
        revision = RevisionRecord.model_validate_json(
            self.request(
                "POST",
                f"/projects/{PROJECT}/revisions",
                expected=201,
                json={
                    "document": document.model_dump(mode="json"),
                    "expected_parent_revision_id": parent_revision_id,
                    "source_candidate_id": str(candidate.candidate_id),
                    "note": "Phase 29F immutable revision acceptance",
                },
            ).text
        )
        require(str(revision.parent_revision_id) == parent_revision_id, "Ancestry")
        unchanged = self.request("GET", f"/projects/{PROJECT}/revisions/{revision_id}").json()
        require(unchanged == original.model_dump(mode="json"), "Original revision immutable")
        history = self.request("GET", f"/projects/{PROJECT}/revisions").json()
        require(len(history) >= 2, "Revision history")
        self.request(
            "POST",
            f"/projects/{PROJECT}/revisions",
            expected=409,
            json={
                "document": document.model_copy(
                    update={"revision_id": uuid4(), "content_hash": None}
                )
                .with_content_hash()
                .model_dump(mode="json"),
                "expected_parent_revision_id": revision_id,
            },
        )
        self.record("revision-history", immutable=True, ancestry=True, stale_parent_rejected=True)
        for format_name, extension in (("JPEG", "jpg"), ("PDF", "pdf"), ("DXF", "dxf")):
            response = self.request(
                "POST",
                f"/projects/{PROJECT}/exports",
                json={
                    "revision_id": str(revision.revision_id),
                    "candidate_id": str(candidate.candidate_id),
                    "format": format_name,
                },
            )
            manifest = json.loads(
                base64.urlsafe_b64decode(response.headers["X-Vastudraw-Export-Manifest"])
            )
            require(manifest["revision_id"] == str(revision.revision_id), "Exact export revision")
            require(
                response.headers["X-Vastudraw-Source-Hash"] == revision.plan_document_hash,
                "Exact export plan hash",
            )
            require(
                hashlib.sha256(response.content).hexdigest()
                == response.headers["X-Vastudraw-Artifact-Sha256"],
                "Export artifact hash",
            )
            (EVIDENCE / f"export-{revision.revision_id}.{extension}").write_bytes(response.content)
            self.record(
                f"export-{extension}",
                bytes=len(response.content),
                exact_revision=True,
                artifact_hash_valid=True,
            )
        self.request(
            "POST",
            f"/projects/{PROJECT}/exports",
            expected=404,
            json={
                "revision_id": str(revision.revision_id),
                "candidate_id": str(uuid4()),
                "format": "PDF",
            },
        )
        self.record("export-wrong-candidate", rejected=True)
        decision = self.request(
            "GET", f"/billing/projects/{PROJECT}/generation-authorization"
        ).json()
        # Billing reports actual grants without generation's explicit development bypass.
        require(
            decision["reason"] != "development_bypass", "Billing route reports actual entitlement"
        )
        if not decision["allowed"]:
            require(decision["consumption"] is None, "Denied entitlement must not consume quota")
        self.record(
            "actual-billing-authorization",
            allowed=decision["allowed"],
            reason=decision["reason"],
            consumption=decision["consumption"],
            generation_bypass_separate=True,
        )
        (EVIDENCE / f"persistence-{revision.revision_id}.json").write_text(
            json.dumps(
                {
                    "revision_id": str(revision.revision_id),
                    "plan_hash": revision.plan_document_hash,
                    "revision_count": len(history),
                }
            ),
            encoding="utf-8",
        )
        self.persistence()
        self.record(
            "browser-checklist",
            remaining=[
                "manual-editor",
                "undo",
                "redo",
                "desktop",
                "mobile",
                "loading",
                "empty",
                "rendered-errors",
            ],
            browser_exercised=False,
        )

    def persistence(self) -> None:
        snapshots = []
        for item in EVIDENCE.glob("persistence-*.json"):
            try:
                UUID(item.stem.removeprefix("persistence-"))
            except ValueError:
                continue
            snapshots.append(item)
        require(bool(snapshots), "Saved persistence snapshot required")
        path = max(snapshots, key=lambda item: item.stat().st_mtime)
        expected = json.loads(path.read_text())
        project = self.request("GET", f"/projects/{PROJECT}").json()
        require(
            project["current_revision_id"] == expected["revision_id"],
            "Current revision persistence",
        )
        revision = self.request(
            "GET", f"/projects/{PROJECT}/revisions/{expected['revision_id']}"
        ).json()
        require(revision["plan_document_hash"] == expected["plan_hash"], "Plan hash persistence")
        self.record("persistent-reopen", revision=expected["revision_id"], hash_valid=True)

    def uploads(self) -> None:
        for extension, media in (
            ("png", "image/png"),
            ("jpg", "image/jpeg"),
            ("pdf", "application/pdf"),
        ):
            path = ROOT / f".local/ollama-vastu-smoke.{extension}"
            intake = self.request(
                "POST",
                f"/projects/{PROJECT}/generation-intakes",
                expected=201,
                data={"prompt": "Analyze this residential reference; geometry remains advisory."},
                files={"files": (path.name, path.read_bytes(), media)},
            ).json()
            analysis = self.request(
                "POST",
                f"/projects/{PROJECT}/generation-intakes/{intake['intake_id']}/plan-analysis",
            ).json()
            from ai_vastu.plan_intake.models import PlanAnalysisResult

            result = PlanAnalysisResult.model_validate_json(json.dumps(analysis))
            require(result.recognition.provider == "ollama_local", "Recognition provider")
            require(result.recognition.model == MODEL, "Recognition model")
            require(
                result.content_hash == result.compute_content_hash(), "Recognition analysis hash"
            )
            self.record(f"upload-recognition-{extension}", provider="ollama_local", model=MODEL)
        self.negative_uploads()

    def negative_uploads(self) -> None:
        for label, filename, data, media, status in (
            ("bad-image", "invalid.png", b"not an image", "image/png", 422),
            ("corrupt-pdf", "invalid.pdf", b"%PDF-1.7\ncorrupt", "application/pdf", 422),
            ("oversized-input", "large.png", b"x" * (20 * 1024 * 1024 + 1), "image/png", 413),
        ):
            self.request(
                "POST",
                f"/projects/{PROJECT}/generation-intakes",
                expected=status,
                data={"prompt": "Invalid reference acceptance"},
                files={"files": (filename, data, media)},
            )
            self.record(label, http_status=status, fail_closed=True)

    def unavailable(self) -> None:
        self.request(
            "POST",
            f"/confirmed-generation/projects/{PROJECT}/alternatives",
            expected=503,
            json={"draft_id": DRAFT, "accept_profile_defaults": True, "max_alternatives": 1},
        )
        self.record("ollama-unavailable-api", http_status=503, fail_closed=True)

    def revision(self) -> None:
        from ai_vastu.architectural_brain.revisions import interpret_revision

        project = self.request("GET", f"/projects/{PROJECT}").json()
        base = project["current_revision_id"]
        require(base is not None, "Saved revision required")
        before = self.request("GET", f"/projects/{PROJECT}/revisions/{base}").json()
        intent = interpret_revision(
            project_id=UUID(PROJECT),
            base_revision_id=UUID(base),
            request="Make the living room 1 foot wider.",
        )
        require(intent.authoritative_geometry is False, "Revision is advisory only")
        require(
            intent.preserve_unmentioned_requirements is True, "Preserve unmentioned requirements"
        )
        require(len(intent.directives) > 0, "Nonempty revision interpretation")
        after = self.request("GET", f"/projects/{PROJECT}/revisions/{base}").json()
        require(before == after, "AI revision must not mutate canonical revision")
        self.record(
            "ai-revision-interpretation",
            directives=len(intent.directives),
            authoritative_geometry=False,
            canonical_unchanged=True,
        )

    def text_requirements(self) -> None:
        from ai_vastu.requirements.models import ConfirmedRequirements, RequirementDraft

        project_id = str(uuid4())
        project = self.request(
            "POST",
            "/projects",
            expected=201,
            json={"project_id": project_id, "name": "Phase 29F synthetic text acceptance"},
        ).json()
        require(project["project_id"] == project_id, "Created project identity")
        require(
            self.request("GET", f"/projects/{project_id}").json() == project,
            "Created project persistence",
        )
        self.record("create-read-project", project_id=project_id, persistence=True)
        prompt = (
            "Residential plot width 9000 mm, depth 12000 mm. North rotation 0 degrees. "
            "Road on the east and east-facing entrance. One ground floor, two bedrooms, "
            "no parking. Include living room, kitchen, dining room and one common toilet. "
            "Use balanced soft Vastu influence. All dimensions are in integer millimetres."
        )
        payload = self.request(
            "POST", "/requirements/interpret", data={"project_id": project_id, "prompt": prompt}
        ).json()
        draft = RequirementDraft.model_validate(payload["draft"])
        require(
            draft.provider == "ollama_local" and draft.model == MODEL, "Requirements provenance"
        )
        require(str(draft.project_id) == project_id, "Requirements project identity")
        require(
            str(draft.user_id) == os.environ["AI_VASTU_DEV_USER_ID"], "Requirements user identity"
        )
        for field in (
            draft.plot_width_mm,
            draft.plot_depth_mm,
            draft.north_rotation_deg,
            draft.road_side,
            draft.entrance_facing,
            draft.floor_count,
            draft.bedroom_count,
            draft.parking_count,
        ):
            if field is not None:
                require(
                    field.requires_confirmation, "AI proposal requires explicit user confirmation"
                )
        self.record(
            "text-ai-interpretation",
            provider=draft.provider,
            model=draft.model,
            advisory=True,
            draft_id=str(draft.draft_id),
            ready_for_confirmation=payload["ready_for_confirmation"],
        )
        # Explicit synthetic user confirmation of known input, never repair of AI
        # proposals or an assertion that inference is authoritative.
        confirmed = ConfirmedRequirements.model_validate(
            {
                "draft_id": draft.draft_id,
                "project_id": project_id,
                "user_id": draft.user_id,
                "user_confirmed": True,
                "plot_width_mm": 9000,
                "plot_depth_mm": 12000,
                "north_rotation_deg": 0,
                "road_side": "E",
                "entrance_facing": "E",
                "floor_count": 1,
                "bedroom_count": 2,
                "parking_count": 0,
                "vastu_mode": "balanced",
                "rooms": [
                    {"room_type": "bedroom", "quantity": 2},
                    {"room_type": "living", "quantity": 1},
                    {"room_type": "kitchen", "quantity": 1},
                    {"room_type": "dining", "quantity": 1},
                    {"room_type": "common_toilet", "quantity": 1},
                ],
            }
        )
        response = self.request(
            "POST",
            f"/requirements/drafts/{draft.draft_id}/confirm",
            json=confirmed.model_dump(mode="json"),
        ).json()
        require(response["confirmed"] == confirmed.model_dump(mode="json"), "Exact confirmation")
        persisted = self.request("GET", f"/requirements/drafts/{draft.draft_id}/confirmed").json()
        require(
            persisted["confirmed"] == response["confirmed"], "Confirmed requirements persistence"
        )
        self.record(
            "explicit-requirements-confirmation",
            project_id=project_id,
            draft_id=str(draft.draft_id),
            canonical_units="integer_mm",
            persistence=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=(
            "vastu",
            "generation",
            "remainder",
            "uploads",
            "persistence",
            "unavailable",
            "revision",
            "basic",
            "negative_uploads",
            "text_requirements",
        ),
    )
    args = parser.parse_args()
    guard_environment()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    acceptance = Acceptance()
    status = "PASS"
    try:
        getattr(acceptance, args.mode)()
    except Exception as exc:
        status = "FAIL"
        # Exception messages may contain model/client text, so log type only.
        result = {"step": args.mode, "status": status, "error_type": type(exc).__name__}
        if isinstance(exc, AcceptanceFailure):
            result["diagnostic"] = str(exc)
        acceptance.results.append(result)
        print(json.dumps(result), flush=True)
    finally:
        acceptance.client.close()
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        (EVIDENCE / f"{args.mode}-{timestamp}.json").write_text(
            json.dumps(
                {"mode": args.mode, "status": status, "results": acceptance.results}, indent=2
            ),
            encoding="utf-8",
        )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
