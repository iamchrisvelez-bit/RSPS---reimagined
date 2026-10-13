# RSPS Item Studio — Project Roadmap

Living milestone tracker. Update status as work lands.

## Current status

**Milestone 1 — Foundation:** in progress

Next step: application shell and project workspace (create/open/save).

## Milestones

### Milestone 1 — Foundation (in progress)

1. Application shell and project workspace (create/open/save)
2. 3D viewport with load, camera, lighting, inspection
3. Import at least OBJ into studio mesh
4. Item project structure on disk (model, texture, color, animation, effect, stats sections)
5. Basic item-stat editor
6. Validation report for missing/invalid project data
7. Adapter interfaces + OpenRune adapter skeleton (no fake full export)
8. Seed `PROJECT_ROADMAP.md`, `ARCHITECTURE.md`, `COMPATIBILITY.md`

**Success criteria:** create project → import OBJ → edit stats/colors stubs → validate → see clear adapter “not yet implemented” export path without corrupting any game files.

### Milestone 2 — OpenRune definition + model path (planned)

- Verify OpenRune-FileStore / OSRS item definition and model formats against real data
- Implement definition codec + staging export + integration report
- Model codec as formats are confirmed
- Backup-on-write into user-selected cache/server paths

### Milestone 3 — Materials, recolor, richer preview (planned)

- Texture pipeline, transparency, palette/recolor live preview
- Stronger material editor and UV inspection

### Milestone 4 — Animation bindings and preview (planned)

- Wire idle/attack/special/equip bindings to verified revision data
- Playback in viewport where formats allow

### Milestone 5 — Effects editor (planned)

- Frame/action-triggered effects; preview subset; export where supported

### Milestone 6 — Additional revision adapters (planned)

- Implement Rev317 (and others) behind the same abstractions
- Cross-revision project reuse where formats allow
