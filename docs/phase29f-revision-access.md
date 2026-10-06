# Changed saved-plan access guard

The generic revision append API checks deterministic pedestrian and vehicle access
when an existing single-floor confirmed plan changes room polygons or types,
walls, openings, or stairs. The confirmed marker is checked on both revisions.
Removing saved parking bays also fails closed. Stale parent requests return 409
before access qualification; the repository still checks ancestry atomically.

This bounded guard does not requalify initial imports, existing multi-floor
contracts, or physically identical legacy snapshots. Old revisions remain
readable and immutable. It does not replace full architectural validation or
change Vastu, wet-stack, schema, or solver geometry authority.
