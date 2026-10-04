# Phase 29 NVIDIA NIM Runtime

Checked against the official NVIDIA API Catalog on 2026-10-01.

## Hosted model verification

| Role | Exact model ID | Hosted endpoint | Modalities | Context | Structured output / tools |
|---|---|---|---|---:|---|
| Active text primary | `nvidia/nemotron-3-ultra-550b-a55b` | Free hosted endpoint available | text -> text | 1M | Passed the live real-`RequirementDraft` contract. Structured output remains strict-prompted and application-validated; the unsupported `response_format` request field is not sent. |
| Inactive historical candidate | `nvidia/nemotron-3.5-lightning-30b-a3b` | Free hosted endpoint available | text -> text | 1M | `NOT_QUALIFIED_TIMEOUT`; it is neither active nor an automatic fallback. |
| Plan recognition candidate | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | Free hosted endpoint available | image, video, audio, text -> text | 262K | Model card explicitly lists JSON output and tool calling. JPEG and PNG are documented image inputs. Raw PDF is not treated as a qualified input. |

All hosted calls use:

- base URL: `https://integrate.api.nvidia.com/v1`;
- endpoint: `/chat/completions`;
- credential: server-side `NVIDIA_API_KEY`.

Sources:

- <https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b?nim=hosted>
- <https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b?nim=hosted>
- <https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning?nim=hosted>
- <https://docs.nvidia.com/nim/large-language-models/1.5.0/structured-generation.html>
- <https://docs.nvidia.com/nim/vision-language-models/1.1.0/structured-generation.html>

Catalog metadata establishes advertised availability and capabilities, not
Vastudraw compatibility. Exact RequirementDraft and plan-intake compatibility
is recorded only after the direct live gates exercise the real adapters.

## Active environment contract

```dotenv
NVIDIA_API_KEY=
AI_VASTU_NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
AI_VASTU_NVIDIA_PRIMARY_MODEL=nvidia/nemotron-3-ultra-550b-a55b
AI_VASTU_NVIDIA_VISION_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
AI_VASTU_REQUIREMENTS_PROVIDER=nvidia_nim
AI_VASTU_ARCHITECT_PROVIDER=nvidia_nim
AI_VASTU_VASTU_PROVIDER=nvidia_nim
AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER=nvidia_nim
AI_VASTU_REVISION_PROVIDER=nvidia_nim
AI_VASTU_PLAN_RECOGNITION_PROVIDER=nvidia_nim
```

OpenRouter and Gemini adapters are legacy/inactive. The NVIDIA profile does not
read their credentials and has no runtime fallback to either provider.

Ultra is the sole active text model. Hosted-inference `unavailable` and
`timeout` failures may receive one immediate retry of that exact same model,
within the original total provider deadline. Authentication, request rejection,
rate limiting, malformed JSON, application validation, and provenance failures
are never retried. Nano Omni remains the sole vision candidate and uses the same
bounded transient-only retry rule.

## Authority and media boundaries

NVIDIA output remains advisory and is validated by the existing application
schemas. Application-owned identities and provenance are injected locally.
Plan-recognition envelope, orientation, and room observations remain
confirmation-required. Canonical geometry is unchanged until the existing user
confirmation path accepts observations.

PDFs are rendered locally, in memory, into bounded ordered PNG pages before the
vision call. The runtime does not claim or use native PDF support and does not
introduce another cloud parser.

## Qualification and entitlement

The free hosted API Catalog endpoint is a prototype/development service.
Successful direct probes may qualify development/staging, but do not qualify a
production deployment.

`NVIDIA_NIM_PRODUCTION_ENTITLEMENT = BLOCKED_HUMAN_ACTION`

Production requires an explicit NVIDIA AI Enterprise or otherwise appropriate
production endpoint, entitlement, support, quota, and data-handling arrangement.
