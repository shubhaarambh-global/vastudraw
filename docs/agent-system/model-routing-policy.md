# Vastudraw Model Routing Policy

This policy governs development agents and skills. It does not change
Vastudraw's product runtime providers (OpenRouter and direct Gemini).

## Required profile

GPT-5.6 Sol Medium is the default and required model/effort for every
Vastudraw Agent OS role, skill, and agentic development task.

A different model or reasoning effort requires explicit user approval. Do not
automatically escalate because work is difficult, security-sensitive,
architecture-sensitive, release-critical, payment-related, or
authentication-related.

If GPT-5.6 Sol Medium is temporarily unavailable, pause and retry it. Do not
silently switch model family or effort.

## Model Router responsibility

The Model Router remains required before substantial delegation. It routes:

- which role should handle each task;
- whether work should be parallel or sequential;
- what context and skills each role needs;
- what deterministic tests and independent reviewers are required;
- whether a decision requires human review.

It does not select a different model or reasoning effort automatically. Every
role uses GPT-5.6 Sol Medium.

## Reliability sequence

When work cannot be resolved reliably at Medium:

1. try a second independent agent;
2. run adversarial review;
3. involve Architecture Guardian or Security Reviewer;
4. gather more evidence;
5. reduce or split the task;
6. escalate the decision to the human user.

Quality is established through role separation, independent review,
deterministic tests, and evidence-based release auditing, not silent model
escalation.
