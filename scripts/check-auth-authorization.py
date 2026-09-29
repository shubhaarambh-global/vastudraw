from pathlib import Path
from uuid import UUID

from ai_vastu.auth import (
    AuthConfigurationError,
    AuthenticationError,
    DevelopmentAccessTokenVerifier,
    create_access_token_verifier_from_environment,
)
from ai_vastu.release import ReleaseGateStatus, evaluate_production_mvp_readiness

ROOT = Path(__file__).resolve().parents[1]

user_id = UUID("19191919-1919-1919-1919-191919191919")
verifier = DevelopmentAccessTokenVerifier("phase19-test-token", user_id)
assert verifier.verify("phase19-test-token").user_id == user_id
try:
    verifier.verify("wrong-token")
except AuthenticationError:
    pass
else:
    raise AssertionError("Development verifier accepted an invalid token.")

try:
    create_access_token_verifier_from_environment({"APP_ENV": "production"})
except AuthConfigurationError:
    pass
else:
    raise AssertionError("Production authentication did not fail closed without Supabase.")

migration = (
    ROOT / "infra/postgres/migrations/202609150002_phase19_project_ownership.sql"
).read_text(encoding="utf-8")
assert "ai_vastu_project_owners" in migration
assert "ENABLE ROW LEVEL SECURITY" in migration
assert "REVOKE ALL" in migration

api_source = (ROOT / "apps/api/app/main.py").read_text(encoding="utf-8")
assert "CurrentUserDependency" in api_source
assert "_require_project_owner" in api_source
assert 'allow_headers=["Authorization", "Content-Type", "Idempotency-Key"]' in api_source

web_source = (ROOT / "apps/web/src/components/dashboard/DashboardPage.tsx").read_text(
    encoding="utf-8"
)
assert "DashboardPage" in web_source
workspace_source = (ROOT / "apps/web/src/components/dashboard/useWorkspaceProjects.ts").read_text(
    encoding="utf-8"
)
assert "useWorkspaceProjects" in web_source
assert "listProjects" in workspace_source
assert "/editor?project=" in web_source

report = evaluate_production_mvp_readiness(ROOT)
auth_gate = next(item for item in report.gates if item.code == "AUTHORIZATION_IMPLEMENTED")
assert auth_gate.status is ReleaseGateStatus.PASS
assert "AUTHORIZATION_NOT_IMPLEMENTED" not in report.blocker_codes
assert report.blocker_count == 0

print(
    "Auth/authorization wired: provider=supabase-jwks, project_ownership=true, "
    "dashboard=true, release_blocker_removed=true"
)
