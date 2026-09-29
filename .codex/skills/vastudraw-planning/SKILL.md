---
name: vastudraw-planning
description: Plan complex Vastudraw changes before implementation, including scope, affected files, invariants, risks, fixtures, tests, and rollback considerations.
---
# Vastudraw Planning

For complex work use Best-of-N planning with two independent planner subagents.

Each returns:
- scope/non-goals
- existing components to reuse
- protected invariants
- files likely affected
- migration/live risks
- fixture strategy
- validation matrix
- definition of done

Then ask the Architecture Guardian to challenge both.
Coordinator synthesizes the final plan.
Prefer reuse and narrow changes.
