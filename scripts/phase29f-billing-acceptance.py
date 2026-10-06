"""Real loopback billing boundary acceptance with an isolated SQLite fixture."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

from ai_vastu.billing.service import BillingService, development_billing_bypass_enabled
from ai_vastu.billing.sqlite_repository import SqliteBillingRepository

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    fixture = ROOT / ".local/phase29f-evidence" / f"billing-boundary-{uuid4()}"
    fixture.mkdir(parents=True)
    env = dict(os.environ)
    assert env.get("APP_ENV") == "development"
    assert env.get("AI_VASTU_PAYMENT_GATEWAY") == "disabled"
    assert not env.get("AI_VASTU_DATABASE_URL", "").strip()
    for selector in (
        "REQUIREMENTS",
        "ARCHITECT",
        "VASTU",
        "ARCHITECTURAL_BRAIN",
        "REVISION",
        "PLAN_RECOGNITION",
    ):
        assert env.get(f"AI_VASTU_{selector}_PROVIDER") == "ollama_local"
    user = str(uuid4())
    env.update(
        AI_VASTU_DEV_USER_ID=user,
        AI_VASTU_DEV_BILLING_BYPASS="0",
        AI_VASTU_SQLITE_PATH=str(fixture / "projects.sqlite3"),
        AI_VASTU_BILLING_SQLITE_PATH=str(fixture / "billing.sqlite3"),
        AI_VASTU_REQUIREMENTS_PATH=str(fixture / "requirements"),
        AI_VASTU_GENERATION_UPLOAD_ROOT=str(fixture / "intakes"),
    )
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    with (fixture / "server.log").open("w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}",
                trust_env=False,
                headers={"Authorization": f"Bearer {env['AI_VASTU_DEV_BEARER_TOKEN']}"},
                timeout=10,
            ) as client:
                for _ in range(100):
                    try:
                        if client.get("/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    assert process.poll() is None, "Fixture API stopped"
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Fixture API startup failed")

                def call(method: str, route: str, status: int = 200, **kwargs: object) -> dict:
                    response = client.request(method, route, **kwargs)
                    assert response.status_code == status, f"{route}: {response.status_code}"
                    return response.json()

                projects = [
                    call("POST", "/projects", 201, json={"name": f"Isolated limit fixture {i}"})[
                        "project_id"
                    ]
                    for i in range(3)
                ]
                first, paid, denied = projects
                assert (
                    call("POST", f"/billing/projects/{first}/register")["source"]
                    == "free_trial_pending"
                )
                call("POST", f"/billing/projects/{paid}/register", 402)
                assert call("GET", f"/billing/projects/{first}/generation-authorization")["allowed"]
                call("POST", f"/billing/projects/{first}/generation-succeeded")
                assert (
                    call("GET", f"/billing/projects/{first}/generation-authorization")["reason"]
                    == "free_generation_used"
                )
                call("POST", f"/billing/projects/{first}/generation-succeeded", 402)
                # Synthetic local repository fixture, never a payment-provider call.
                repository = SqliteBillingRepository(fixture / "billing.sqlite3")
                try:
                    assert BillingService(repository).apply_one_time_purchase(
                        f"fixture-{uuid4()}",
                        user,
                        "project_single",
                        provider="local_acceptance_fixture",
                    )
                finally:
                    repository.close()
                assert (
                    call("POST", f"/billing/projects/{paid}/register")["source"] == "project_credit"
                )
                assert call("GET", "/billing/me")["project_credits"] == 0
                call("POST", f"/billing/projects/{denied}/register", 402)
                assert (
                    call("GET", f"/billing/projects/{denied}/generation-authorization")["reason"]
                    == "project_not_entitled"
                )
                assert (
                    call("GET", f"/billing/projects/{paid}/generation-authorization")["reason"]
                    == "paid_project"
                )
                call("POST", f"/billing/projects/{paid}/generation-succeeded")
                assert call("GET", f"/billing/projects/{paid}/generation-authorization")["allowed"]
                assert call("GET", f"/projects/{paid}")["project_id"] == paid
                call("POST", "/billing/checkout", 503, json={"sku": "project_single"})
            original_env = os.environ.get("APP_ENV")
            original_bypass = os.environ.get("AI_VASTU_DEV_BILLING_BYPASS")
            try:
                os.environ["AI_VASTU_DEV_BILLING_BYPASS"] = "1"
                repository = SqliteBillingRepository(fixture / "billing.sqlite3")
                try:
                    for runtime in ("staging", "production"):
                        os.environ["APP_ENV"] = runtime
                        assert not development_billing_bypass_enabled()
                        assert (
                            not BillingService(
                                repository, development_bypass=development_billing_bypass_enabled()
                            )
                            .authorize_generation(user, denied)
                            .allowed
                        )
                finally:
                    repository.close()
            finally:
                for key, value in (
                    ("APP_ENV", original_env),
                    ("AI_VASTU_DEV_BILLING_BYPASS", original_bypass),
                ):
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            result = {
                "status": "PASS",
                "live_http": True,
                "isolated_sqlite": True,
                "free_generation_exhausted": True,
                "project_credit_exhausted": True,
                "existing_paid_project_usable": True,
                "denial_http": 402,
                "payment_gateway_disabled": True,
                "staging_production_bypass": False,
                "generation_allowance_checked": "authorization_and_success_accounting",
            }
            (fixture / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, sort_keys=True))
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
