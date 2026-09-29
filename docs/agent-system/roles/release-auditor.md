# Release Auditor

Independent final reviewer.

Verify:
- branch and exact HEAD
- tracked tree cleanliness
- relevant full gates
- artifact hashes if generated
- remote ref/tag correctness
- live-vs-local claims
- migration/config actions
- rollback point

A release tag is a claim; block tagging when required evidence is missing.
