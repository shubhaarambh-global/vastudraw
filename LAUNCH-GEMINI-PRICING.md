# Launch Gemini + pricing patch (Part A)

This overlay changes only contracts that were present in `provider-contracts.txt`.

Implemented:
- Gemini 2.5 Flash live requirements provider using existing `httpx` boundary.
- Text + JPEG/PNG/PDF inline multimodal input.
- Structured `RequirementDraft` JSON output with application identity restored server-side.
- `httpx` promoted to a production dependency.
- Pricing changed to ₹499 / ₹4,899 / ₹9,999 / ₹69,999.
- Catalog metadata exposes 3 generations/project for Single and 5/project for 10-pack.
- Production configuration accepts either Gemini or OpenAI and validates provider-specific credentials.
- OpenAI provider remains intact.

Not yet enforced in Part A:
- The 3/5 successful-generation counters are metadata only. Enforcement requires exact
  `sqlite_repository.py`, `postgres_repository.py`, and Phase 23 billing SQL contracts,
  which were not included in `provider-contracts.txt`.
- PhonePe is not added here; Razorpay remains unchanged until its replacement/parallel
  provider adapter is implemented.

Do not apply database migrations for generation caps until Part B is completed.
