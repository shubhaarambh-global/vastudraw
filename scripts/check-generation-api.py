from generation_smoke_fixture import generation_request

from ai_vastu.generation import GenerationDisposition, generate_architectural_plan

request = generation_request()
first = generate_architectural_plan(request)
second = generate_architectural_plan(request)

if first != second or first.content_hash != second.content_hash:
    raise SystemExit("Architectural generation pipeline is not deterministic.")
if first.disposition is not GenerationDisposition.REJECTED:
    raise SystemExit(f"Expected an explicitly un-opened draft candidate, got {first.disposition}.")
if first.geometry_result is None or first.validation_result is None:
    raise SystemExit("Accepted generation is missing geometry or validation.")
if first.validation_result.report.valid:
    raise SystemExit("Draft without explicit openings must fail circulation validation.")
error_codes = {item.message_code for item in first.validation_result.report.errors}
if "UNREACHABLE_ROOM_FROM_EXTERIOR_ACCESS" not in error_codes:
    raise SystemExit("Expected explicit circulation failure for draft without openings.")

print(
    "Generation API deterministic: "
    f"status={first.planner_result.status.value}, "
    f"rooms={len(first.geometry_result.floor.rooms)}, "
    f"disposition={first.disposition.value}, hash={first.content_hash}"
)
