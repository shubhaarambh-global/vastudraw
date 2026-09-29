# Vastudraw Multi-Agent Team Prompt

Use the repository instructions and relevant skills.

For a substantial task:

0. Model Router assigns roles, sequencing/parallelism, context, skills, tests,
   reviewers, and human-review conditions. Every role uses GPT-5.6 Sol Medium;
   any model or reasoning-effort change requires explicit user approval.

1. Coordinator retrieves relevant knowledge-graph context and protected contracts.
2. Two planners independently propose bounded plans.
3. Architecture Guardian challenges both.
4. Coordinator synthesizes one plan.
5. Implementation work is divided only by disjoint file/domain ownership or isolated worktrees.
6. Fixture Engineer builds representative positive/boundary/failure fixtures.
7. Regression Tester and Adversarial Tester evaluate independently.
8. Security Reviewer participates for auth/payments/providers/uploads/production config.
9. QA Reviewer challenges the integrated diff and evidence.
10. Coordinator fixes findings and reruns gates.
11. Release Auditor verifies exact qualification claims.
12. Memory Curator records only durable verified knowledge.

Agents share conclusions/evidence, not private chain-of-thought.
Do not let specialist agents independently tag releases or redefine protected product/architecture rules.
