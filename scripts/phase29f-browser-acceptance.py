"""Real local Edge journey. Playwright is installed only under .local."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".local/phase29f-browser-tools"))


def main() -> None:
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=(
            "journey",
            "layouts",
            "editor",
            "exports",
            "navigation",
            "outage",
            "upload",
            "states",
        ),
    )
    parser.add_argument("--project")
    parser.add_argument("--resume-revision", type=Path)
    parser.add_argument("--viewport-width", type=int, choices=(1440, 768, 390), default=1440)
    args = parser.parse_args()
    directory = (
        ROOT
        / ".local/phase29f-evidence"
        / ("browser-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + args.mode)
    )
    directory.mkdir(parents=True)
    results: list[dict] = []

    def record(step: str, **details: object) -> None:
        result = {"step": step, "status": "PASS", **details}
        results.append(result)
        (directory / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(json.dumps(result, sort_keys=True), flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            headless=True,
        )
        context = browser.new_context(
            viewport={"width": args.viewport_width, "height": 1000}, accept_downloads=True
        )
        context.route(
            "**/*",
            lambda route: (
                route.continue_()
                if urlparse(route.request.url).hostname in {"127.0.0.1", "localhost"}
                or route.request.url.startswith(("data:", "blob:"))
                else route.abort()
            ),
        )
        page = context.new_page()
        page.set_default_timeout(60_000)
        if args.mode == "journey":

            def reject_failed_api(response):
                if response.url.startswith("http://127.0.0.1:8000/") and response.status >= 400:
                    record(
                        "api-error-observed",
                        http_status=response.status,
                        endpoint=urlparse(response.url).path,
                    )
                    raise RuntimeError(f"Browser API HTTP {response.status}")

            page.on("response", reject_failed_api)
        project = args.project
        if args.mode == "navigation":
            assert project
            editor_url = f"http://127.0.0.1:3000/editor?project={project}"
            page.goto(editor_url, wait_until="networkidle")
            page.get_by_role("toolbar").wait_for()
            page.goto("http://127.0.0.1:3000/projects", wait_until="networkidle")
            page.go_back(wait_until="networkidle")
            assert page.url == editor_url
            page.get_by_role("toolbar").wait_for()
            page.go_forward(wait_until="networkidle")
            assert page.url == "http://127.0.0.1:3000/projects"
            record("browser-back-forward-saved-project")
        if args.mode == "states":
            page.goto("http://127.0.0.1:3000/projects", wait_until="networkidle")
            page.get_by_label("Search projects").fill("phase29f-no-such-project-unique-filter")
            assert page.locator(".saas-project-table-row").count() == 0
            record("projects-empty-search")
            page.goto("http://127.0.0.1:3000/editor?project=00000000-0000-0000-0000-000000000099")
            page.get_by_role("heading", name="Could not load this project").wait_for()
            page.get_by_role("button", name="Retry", exact=True).wait_for()
            page.screenshot(path=str(directory / "safe-project-error.png"), full_page=True)
            record("browser-safe-project-error")
            page.goto("http://127.0.0.1:3000/generation", wait_until="networkidle")
            page.get_by_role("button", name="Generate new plan").click()
            assert page.get_by_role("button", name="Next", exact=True).is_disabled()
            record("incomplete-requirements-disabled")
        if args.mode == "upload":
            assert project
            page.goto("http://127.0.0.1:3000/generation", wait_until="networkidle")
            page.get_by_role("button", name="Analyze my plan").click()
            page.locator(".generation-project-field select").select_option(project)
            page.get_by_label("Generation / plan-analysis prompt").fill(
                "Audit this synthetic acceptance reference; keep all geometry advisory."
            )
            page.locator('input[type="file"]').set_input_files(
                str(ROOT / ".local/ollama-vastu-smoke.png")
            )
            with page.expect_response(
                lambda r: "/generation-intakes" in r.url and r.request.method == "POST"
            ) as intake:
                page.get_by_role("button", name="Save generation brief", exact=True).click()
            assert intake.value.status == 201
            with page.expect_response(
                lambda r: r.url.endswith("/plan-analysis"), timeout=600_000
            ) as analysis:
                page.get_by_role("button", name="Analyze uploaded plan", exact=True).click()
                record("upload-analysis-loading")
            assert analysis.value.status == 200
            page.get_by_text("Uploaded-plan Vastu audit", exact=True).wait_for()
            record("browser-png-recognition-vastu-advisory")
            page.screenshot(path=str(directory / "upload-advisory.png"), full_page=True)
        if args.mode == "journey":
            page.goto("http://127.0.0.1:3000/dashboard")
            page.get_by_role("heading", name="Dashboard", exact=True).wait_for()
            record("dashboard")
            page.goto("http://127.0.0.1:3000/projects")
            page.wait_for_load_state("networkidle")
            page.get_by_role("button", name="+ New project", exact=True).click()
            page.get_by_label("Project name").fill("Phase29F browser empty fixture")
            with page.expect_response(
                lambda r: r.url.endswith("/projects") and r.request.method == "POST"
            ) as creation:
                page.get_by_role("button", name="Create project", exact=True).click()
            assert creation.value.status == 201
            empty_id = creation.value.json()["project_id"]
            page.goto(f"http://127.0.0.1:3000/editor?project={empty_id}")
            page.get_by_role(
                "heading", name="This project does not have a PlanDocument revision yet."
            ).wait_for()
            record("project-create-empty-state")
            page.goto("http://127.0.0.1:3000/generation")
            page.wait_for_load_state("networkidle")
            page.get_by_role("button", name="Generate new plan").click()
            page.get_by_label("Project name").fill("Phase29F browser residence")
            page.get_by_label("Length (feet)").fill("50")
            page.get_by_label("Breadth (feet)").fill("30")
            for step in range(5):
                if step == 3:
                    page.locator(".phase26c-counter").filter(has_text="Bathrooms").get_by_role(
                        "button"
                    ).last.click()
                page.get_by_role("button", name="Next", exact=True).click()
            with page.expect_response(
                lambda r: r.url.endswith("/alternatives") and r.request.method == "POST",
                timeout=1_800_000,
            ) as generation:
                page.get_by_role("button", name="Generate plan options", exact=True).click()
                page.get_by_role("button", name="Generating plan options", exact=False).wait_for()
                record("generation-loading-state")
            response = generation.value
            assert response.status == 200, f"Confirmed generation HTTP {response.status}"
            payload = response.json()
            (directory / "generation.json").write_text(json.dumps(payload), encoding="utf-8")
            candidates = payload["candidate_run"]["candidates"]
            assert len(candidates) == 4, f"Expected four alternatives, received {len(candidates)}"
            project = payload["candidate_run"]["project_id"]
            (directory / "project.json").write_text(
                json.dumps({"project_id": project}), encoding="utf-8"
            )
            record("text-interpret-confirm-generation", alternatives=4, project_id=project)
            for index in range(4):
                page.get_by_role("tab").nth(index).click()
                page.locator(".phase26c3-canvas-card svg").wait_for()
                page.screenshot(
                    path=str(directory / f"alternative-{index + 1}.png"), full_page=True
                )
            record("inspect-four-alternatives")
            page.get_by_role("tab").first.click()
            with page.expect_response(lambda r: r.url.endswith("/alternatives/select")) as selected:
                page.get_by_role("button", name="Select this plan", exact=True).click()
            assert selected.value.status == 200
            selection = selected.value.json()
            revision = selection["revision_id"]
            (directory / "selection.json").write_text(json.dumps(selection), encoding="utf-8")
            record("canonical-save", revision_id=revision)
            for export in ("JPEG", "PDF", "DXF"):
                with (
                    page.expect_download() as download,
                    page.expect_response(lambda r: r.url.endswith("/exports")) as artifact,
                ):
                    page.get_by_role("button", name=export, exact=True).click()
                assert artifact.value.status == 200
                manifest = json.loads(
                    base64.urlsafe_b64decode(artifact.value.headers["x-vastudraw-export-manifest"])
                )
                assert manifest["revision_id"] == revision
                path = directory / download.value.suggested_filename
                download.value.save_as(path)
                assert (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    == artifact.value.headers["x-vastudraw-artifact-sha256"]
                )
                record("browser-export-" + export, exact_revision=True)
        if args.mode == "exports":
            assert project
            page.goto(f"http://127.0.0.1:3000/editor?project={project}", wait_until="networkidle")
            panel = page.get_by_role("region", name="Saved revision exports")
            panel.wait_for()
            for export in ("JPEG", "PDF", "DXF"):
                with (
                    page.expect_download() as download,
                    page.expect_response(lambda r: r.url.endswith("/exports")) as artifact,
                ):
                    panel.get_by_role("button", name=export, exact=True).click()
                response = artifact.value
                assert response.status == 200
                request = response.request.post_data_json
                manifest = json.loads(
                    base64.urlsafe_b64decode(response.headers["x-vastudraw-export-manifest"])
                )
                assert manifest["revision_id"] == request["revision_id"]
                assert manifest["candidate_id"] == request["candidate_id"]
                assert manifest["source_plan_hash"] == response.headers["x-vastudraw-source-hash"]
                path = directory / download.value.suggested_filename
                download.value.save_as(path)
                assert (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    == (response.headers["x-vastudraw-artifact-sha256"])
                )
                record(
                    "browser-export-" + export,
                    exact_revision=True,
                    revision_id=manifest["revision_id"],
                )
        if args.mode in {"journey", "editor", "outage"}:
            assert project
            page.goto(f"http://127.0.0.1:3000/editor?project={project}")
            page.get_by_role("toolbar").wait_for()
            record("editor-reopen", project_id=project)
            if args.mode == "outage":
                page.get_by_label("Room dimension change").fill("Make kitchen 100 mm wider")
                with page.expect_response(
                    lambda r: r.url.endswith("/revision-chat"), timeout=60_000
                ) as failed:
                    page.get_by_role("button", name="Save revised plan", exact=True).click()
                assert failed.value.status == 503
                page.get_by_role("alert").filter(has_text="AI provider is unavailable.").wait_for()
                record("ollama-unavailable-ui", http_status=503)
            else:
                if args.resume_revision:
                    revision_payload = json.loads(args.resume_revision.read_text(encoding="utf-8"))
                    record("resume-exact-saved-revision")
                else:
                    page.get_by_label("Room dimension change").fill("Make kitchen 100 mm wider")
                    with page.expect_response(
                        lambda r: r.url.endswith("/revision-chat"), timeout=600_000
                    ) as revised:
                        page.get_by_role("button", name="Save revised plan", exact=True).click()
                        page.get_by_role(
                            "button", name="Generating revision...", exact=True
                        ).wait_for()
                        record("revision-loading-state")
                    if revised.value.status != 200:
                        # Only sanitized server errors, never provider request/response text.
                        failure = {
                            "http_status": revised.value.status,
                            "detail": revised.value.json().get("detail"),
                        }
                        (directory / "revision-error.json").write_text(
                            json.dumps(failure), encoding="utf-8"
                        )
                    assert revised.value.status == 200, f"Revision HTTP {revised.value.status}"
                    revision_payload = revised.value.json()
                    change = revision_payload["dimension_change"]
                    assert change["room_type"] == "kitchen" and change["axis"] == "WIDTH"
                    assert change["applied_mm"] - change["previous_mm"] == 100
                    assert change["applied_mm"] == change["requested_mm"]
                    assert change["rounding_mm"] == 0
                    kitchen = next(
                        room
                        for floor in revision_payload["revision"]["document"]["floors"]
                        for room in floor["rooms"]
                        if room["room_type"] == "kitchen"
                    )
                    xs = [point["x_mm"] for point in kitchen["polygon"]["outer"]]
                    assert max(xs) - min(xs) == change["applied_mm"]
                    (directory / "revision.json").write_text(
                        json.dumps(revision_payload), encoding="utf-8"
                    )
                    page.get_by_role("toolbar").wait_for()
                    page.get_by_role("status").filter(has_text="(requested").wait_for()
                    record("local-ollama-revision-chat", exact_increase_mm=100)
                page.reload()
                page.get_by_role("toolbar").wait_for()
                history = page.get_by_role("region", name="Revision history")
                history.locator("li").nth(1).wait_for()
                assert history.locator("li").count() >= 2
                record("history-reopen-ancestry")
                # Canvas room selection uses the real Konva stage coordinate system.
                canvas = page.locator(".konvajs-content canvas").last
                canvas.scroll_into_view_if_needed()
                page.get_by_role("button", name="Fit", exact=True).click()
                box = canvas.bounding_box()
                assert box
                selected_room = False
                document = revision_payload["revision"]["document"]
                floor = document["floors"][0]
                boundary = (floor.get("boundary") or document["buildable_area"]["polygon"])["outer"]
                min_x, max_x = min(p["x_mm"] for p in boundary), max(p["x_mm"] for p in boundary)
                min_y, max_y = min(p["y_mm"] for p in boundary), max(p["y_mm"] for p in boundary)
                scale = max(
                    0.005,
                    min(
                        5,
                        (box["width"] - 128) / (max_x - min_x),
                        (box["height"] - 128) / (max_y - min_y),
                    ),
                )
                for room in floor["rooms"]:
                    if room.get("locked"):
                        continue
                    outer = room["polygon"]["outer"]
                    center_x = sum(p["x_mm"] for p in outer) / len(outer)
                    center_y = sum(p["y_mm"] for p in outer) / len(outer)
                    x = (box["width"] - (max_x - min_x) * scale) / 2 + (center_x - min_x) * scale
                    y = (box["height"] - (max_y - min_y) * scale) / 2 + (max_y - center_y) * scale
                    canvas.click(position={"x": x, "y": y})
                    if page.get_by_role("button", name="Lock room", exact=True).count():
                        selected_room = True
                        break
                assert selected_room, "Select an unlocked room in the canonical canvas"
                page.get_by_role("button", name="Lock room", exact=True).click()
                assert page.get_by_role("button", name="Undo", exact=True).is_enabled()
                page.get_by_role("button", name="Undo", exact=True).click()
                assert page.get_by_role("button", name="Lock room", exact=True).count()
                page.get_by_role("button", name="Redo", exact=True).click()
                assert page.get_by_role("button", name="Unlock room", exact=True).count()
                record("manual-editor-undo-redo")
                page.get_by_role("button", name="Submit exact edits", exact=True).click()
                with page.expect_response(lambda r: r.url.endswith("/editor-commands")) as edited:
                    page.get_by_role("button", name="Save exact edits", exact=True).click()
                assert edited.value.status == 200
                (directory / "manual-revision.json").write_text(
                    json.dumps(edited.value.json()), encoding="utf-8"
                )
                page.reload()
                page.get_by_role("toolbar").wait_for()
                record("manual-editor-save-reopen")
        if args.mode in {"journey", "editor", "layouts"}:
            for width, height, label in (
                (1440, 1000, "desktop"),
                (768, 1024, "tablet"),
                (390, 844, "mobile"),
            ):
                page.set_viewport_size({"width": width, "height": height})
                for route in (
                    "/dashboard",
                    "/projects",
                    "/generation",
                    f"/editor?project={project}" if project else "/editor",
                ):
                    page.goto("http://127.0.0.1:3000" + route)
                    page.wait_for_timeout(1000)
                    assert not page.evaluate(
                        "document.documentElement.scrollWidth > innerWidth + 1"
                    ), f"Overflow {label} {route}"
                    page.screenshot(
                        path=str(directory / f"{label}-{route.split('?')[0].strip('/')}.png"),
                        full_page=True,
                    )
                record("layout-" + label, width=width)
        browser.close()


if __name__ == "__main__":
    main()
