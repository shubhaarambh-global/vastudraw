# Phase 12 freeze — Interactive 2D editor

Phase 12 introduces the first runnable Next.js/React editor surface.

Frozen behavior:

- Next.js client editor using React, Zustand and Konva/react-konva;
- canonical `PlanDocument` remains the single geometry source;
- drawing `+Y` is explicitly inverted for the Canvas coordinate system;
- pan, zoom, fit, grid, rulers and visibility layers;
- room/wall/opening/dimension selection;
- exact integer-mm staged edits with undo/redo;
- room/wall lock staging;
- wall/opening pending previews;
- edit submission as a revision-bound change set;
- no browser-side claim of solve or validation success.

Not frozen/implemented yet:

- backend application of editor change sets and re-solve orchestration;
- multi-user collaboration;
- export pipelines;
- production authentication;
- Vastu rule content (spec remains DRAFT).
