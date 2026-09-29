---
name: vastudraw-model-router
description: Route Vastudraw work to the correct roles, context, tests, and reviewers. Use GPT-5.6 Sol Medium for all agentic work unless the user explicitly approves another model.
---
# Vastudraw Model Router

Use this skill before spawning subagents or assigning a substantial workstream.

Read:
- `docs/agent-system/model-routing-policy.md`
- `docs/agent-system/model-routing-policy.json`
- `docs/agent-system/roles/model-router.md`

## Procedure

1. Classify task risk: LOW / MEDIUM / HIGH / CRITICAL.
2. Classify ambiguity: LOW / MEDIUM / HIGH.
3. Classify breadth: NARROW / MULTI / SYSTEM.
4. Identify failure cost.
5. Assign the roles, sequencing, context, skills, tests and reviewers needed.
6. Attach explicit human-review triggers.

## Required profile

Every Vastudraw Agent OS role, skill and agentic development task uses:

- GPT-5.6 Sol
- Medium reasoning effort

A different model or reasoning effort requires explicit user approval. Do not
automatically change model or effort because work is difficult,
security-sensitive, architecture-sensitive, release-critical,
payment-related or authentication-related. If the required profile is
temporarily unavailable, pause and retry it rather than silently switching.

## Router responsibility

The Model Router routes:

- which role handles the task;
- parallel or sequential execution;
- required context and skills;
- deterministic tests and independent reviewers;
- whether human review is necessary.

It does not automatically route model family or reasoning effort.

If Medium is insufficient, try a second independent agent, adversarial review,
Architecture Guardian or Security Reviewer, more evidence, and a smaller task
split before escalating the decision to the human user.

## Important

The router governs development agents only. It must not modify the qualified
Vastudraw product runtime AI stack.

Do not treat unavailable model switching as permission to substitute another
profile.
