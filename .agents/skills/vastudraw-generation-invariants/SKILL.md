---
name: vastudraw-generation-invariants
description: >-
  Use whenever modifying Vastudraw architectural generation, requirements
  compilation, Architectural Brain, precedents, CP-SAT solver logic, site
  accounting, circulation, multi-floor generation, vertical cores, candidate
  ranking, or deduplication. Protects authoritative geometry and generation
  invariants. Do not use for unrelated UI-only work.
---

# Vastudraw Generation Invariants

Apply these rules whenever generator behavior is changed.

## Authority model

The authoritative pipeline is:

Brief
→ precedent retrieval
→ candidate-specific topology
→ Architectural Brain
→ Vastu topology evaluation
→ deterministic CP-SAT geometry
→ architectural critic
→ Canonical PlanDocument
→ renderer

Canonical `PlanDocument` is authoritative geometry.

AI may propose:
- intent;
- topology;
- relationships;
- preferences;
- rationale.

AI must not directly author uncontrolled final geometry.

## Constraint precedence

Preserve this hierarchy:

1. confirmed user requirements;
2. hard architectural validity;
3. deterministic geometry invariants;
4. authoritative Vastu hard rules;
5. precedent preferences;
6. AI preferences;
7. soft optimization/scoring.

Lower authority must never overwrite higher authority.

## Site and land invariants

- Do not disguise unexplained residual land as purposeful space.
- Purposeful site space must have a real architectural purpose.
- Ground/site accounting is not equivalent to upper-floor footprint accounting.
- Upper floors must not be forced to consume land as if they own the site.
- Residual or open-to-sky geometry must remain semantically honest.

## Room-program invariants

- Every confirmed required room instance must appear exactly as required.
- Do not silently drop rooms.
- Do not duplicate rooms merely to fill area.
- Combined living/dining must not create an unintended separate dining room.
- Do not balloon parking, toilets, puja, stores, utilities, or circulation to
  artificially fill unused geometry.
- Whole-building program completeness must be independently validated.

## Parking

Parking must represent usable vehicle geometry.

Preserve:
- real frontage/depth constraints;
- appropriate road relationship;
- ground/site semantics;
- bounded area;
- no arbitrary upper-floor parking migration.

## Puja and sanitary separation

Existing hard puja/sanitary separation rules remain authoritative.

Do not:
- allow prohibited shared-wall adjacency;
- weaken rules to improve feasibility;
- invent new Vastu rules that are not present in authoritative project rules.

## Candidate topology

Candidate-specific topology from the ResPlan/Architectural Brain pipeline must
remain candidate-specific.

Do not regress to:
- one averaged topology applied to every candidate;
- candidate diversity based only on labels, IDs, scores, or tiny jitter.

## Circulation

Circulation must be physically traversable.

Do not count as valid access:
- corner-touch contact;
- insufficient shared wall for a doorway;
- traversal through sanitary rooms;
- post-hoc openings invented without geometric support.

A disconnected required room must fail closed.

For multi-floor buildings, vertical access must participate in the complete
building circulation graph.

## Candidate deduplication

Do not revert complete-building spatial equivalence to naive hash equality.

Small solver jitter must not manufacture fake candidate diversity.

Material differences must remain distinct.

When two solved candidates are effectively equivalent, keep the stronger-ranked
representative.

## Multi-floor

Multi-floor generation must be real backend geometry.

Do not fake:
- G+1/G+2/G+3 through frontend state;
- cloned floors;
- unrelated independent floors presented as one building;
- stairs inserted only as decoration.

Stable floor indexing:
- ground = 0;
- first = 1;
- second = 2;
- third = 3;
- etc.

Program distribution must happen at building level before final geometry is
accepted.

## Fail-closed principle

If architectural validity cannot be demonstrated, reject the candidate with
bounded diagnostics rather than silently accepting it.
