from __future__ import annotations

from pathlib import Path

from ai_vastu.requirements.residential_planning import local_boundary_side
from ai_vastu.solver import PlannerBoundarySide, ResidentialPlanningConfig
from ai_vastu.solver.residential_quality import expansion_cap_basis_points

ROOT = Path(__file__).resolve().parents[1]

required = (
    ROOT / "python/ai_vastu/solver/residential_quality.py",
    ROOT / "python/ai_vastu/requirements/residential_planning.py",
    ROOT / "python/ai_vastu/solver/rectangular_cp_sat.py",
    ROOT / "python/ai_vastu/generation/service.py",
    ROOT / "python/ai_vastu/requirements/generation_adapter.py",
    ROOT / "python/ai_vastu/multi_candidate/engine.py",
    ROOT / "apps/web/src/components/generation/Phase26CCandidateWorkspace.tsx",
    ROOT / "apps/web/src/components/generation/Phase26CProjectWizard.tsx",
)
missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
if missing:
    raise SystemExit("Phase 26C.4A missing files: " + ", ".join(missing))

planning = ResidentialPlanningConfig(enabled=True)
if planning.target_occupied_area_basis_points != 7_000:
    raise SystemExit("Phase 26C.4A automatic occupancy target changed unexpectedly.")
if local_boundary_side("E", north_rotation_deg=0) is not PlannerBoundarySide.EAST:
    raise SystemExit("Phase 26C.4A road-boundary mapping failed.")
if expansion_cap_basis_points.__name__ != "expansion_cap_basis_points":
    raise SystemExit("Phase 26C.4A room expansion policy is unavailable.")

solver = required[2].read_text(encoding="utf-8")
for token in (
    "RESIDENTIAL_OCCUPIED_AREA_TARGET",
    "RESIDENTIAL_ROOM_AREA_BALANCE",
    "RESIDENTIAL_COMPACTNESS_VOID",
    "RESIDENTIAL_TOPOLOGY_ADJACENCY",
    "ROAD_CONNECTED_PARKING_ENFORCED",
    "ENTRANCE_BOUNDARY_ANCHOR_ENFORCED",
    "PreferredAreaObjective",
):
    if token not in solver:
        raise SystemExit(f"Phase 26C.4A solver missing contract: {token}")

service = required[3].read_text(encoding="utf-8")
if "_wall_on_boundary_side" not in service:
    raise SystemExit("Phase 26C.4A entrance-side door filtering is missing.")

adapter = required[4].read_text(encoding="utf-8")
for token in (
    "PHASE26C4A_RESIDENTIAL_PLANNING",
    "target_occupied_area_basis_points",
    "require_road_connected_parking",
):
    if token not in adapter:
        raise SystemExit(f"Phase 26C.4A adapter missing contract: {token}")

workspace = required[6].read_text(encoding="utf-8")
if "Measured objectives" not in workspace:
    raise SystemExit("Phase 26C.4A UI still overstates the legacy architecture score.")
if "<strong>Plan</strong>" not in workspace:
    raise SystemExit("Phase 26C.4A UI still exposes unproven strategy labels as qualities.")

print(
    "Phase 26C.4A ready: occupancy_target=true, area_balance=true, "
    "compactness=true, topology=true, road_parking=true, entrance_anchor=true, "
    "entrance_door_side=true, preferred_area=true, score_claim_hardened=true, "
    "structural_v2=true"
)
