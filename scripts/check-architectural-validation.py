from validation_smoke_fixture import validation_request

from ai_vastu.validation import validate_architectural_geometry

request = validation_request()
first = validate_architectural_geometry(request)
second = validate_architectural_geometry(request)
if not first.report.valid:
    codes = ", ".join(item.message_code for item in first.report.errors)
    raise SystemExit(f"Architectural validation smoke failed: {codes}")
if first != second or first.content_hash != second.content_hash:
    raise SystemExit("Architectural validation is not deterministic.")
print(
    "Architectural validation deterministic: "
    f"valid={first.report.valid}, errors={len(first.report.errors)}, "
    f"warnings={len(first.report.warnings)}, hash={first.content_hash}"
)
