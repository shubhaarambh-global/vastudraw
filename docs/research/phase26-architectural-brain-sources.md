# Phase 26 Architectural Brain — Research Register

Research date: 2026-09-18.

## Production-eligible starting sources

### ResPlan
- https://github.com/m-agour/ResPlan
- 17,000 residential plans.
- Vector rooms/walls/doors/windows and typed connectivity graphs.
- Repository states CC BY 4.0 for data and MIT for code.
- Primary precedent-corpus candidate.

### Modified Swiss Dwellings JSON
- https://zenodo.org/records/17294451
- 4,572 room-based geometries with topological dual graphs.
- Verify exact release-license metadata before production ingestion.

### FloorplanQA Layouts
- https://huggingface.co/datasets/OldDelorean/FloorplanQA-Layouts
- 2,000 structured room layouts with boundaries, objects, doors and windows.
- CC BY 4.0.
- Best used for furniture/opening feasibility rather than whole-house retrieval.

## Research-method references

### Graph2Plan
- https://github.com/HanHan55/Graph2plan
- Boundary + layout graph -> floor plan.
- Retrieves precedent layout graphs before generation.

### House-GAN++
- https://openaccess.thecvf.com/content/CVPR2021/html/Nauata_House-GAN_Generative_Adversarial_Layout_Refinement_Network_towards_Intelligent_Computational_Agent_CVPR_2021_paper.html
- Iterative graph-constrained refinement.
- Supports generate -> critique -> repair.

### HouseDiffusion
- https://arxiv.org/abs/2211.13287
- Graph-conditioned vector floorplan generation.
- Explicit room/door polygons, orthogonality, corner sharing and parallelism.

## Indian regulatory reference

### National Building Code of India 2016
- https://www.bis.gov.in/standards/national-building-code/
- Model code for development control/general requirements, fire/life safety,
  structural provisions, services, accessibility and related topics.
- Actual legal applicability depends on state/local authority adoption and bye-laws.

## Restricted/reference-only examples

Do not place non-commercial/research-only datasets into the commercial production
corpus unless separate commercial rights are obtained. Public downloadability is not
sufficient permission.

## Provenance contract

Every imported precedent must retain:
- source_id
- source_record_id
- release/source URL
- license identifier
- attribution
- transform version
- content hash
- import timestamp/version

This permits later source removal/takedown without corrupting project revisions.
