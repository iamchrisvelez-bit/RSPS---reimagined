# RSPS Item Studio — Project Roadmap

Living milestone tracker. Update status as work lands.

## Current status

**Milestone 1 — Foundation:** in progress

Next step: Export staging command + M1 acceptance (Task 10).

### Windows manual check — stat editor & validation (Task 8)

1. `dotnet run --project src/RspsItemStudio.App` on Windows.
2. **File → New project…** — create a project.
3. On **Stats**, clear **Name** (empty), click **Validate** — Validation tab lists `NAME_EMPTY`.
4. Set **Name** to a non-empty value, **Validate** again — `NAME_EMPTY` is gone; `MODEL_MISSING` remains (no inventory mesh yet).
5. Confirm `validation/last-report.json` exists under the project folder after Validate.

### Windows manual check — viewport & OBJ import (Task 9)

1. `dotnet run --project src/RspsItemStudio.App` on Windows.
2. Create or open a project, click **Import OBJ**, choose a `.obj` file.
3. Confirm status bar shows vertex/triangle counts; `models/inventory.mesh.json` and `models/source/<file>.obj` exist.
4. Orbit (left drag), pan (right drag), zoom (wheel); switch **View** combo (Solid / SolidUntextured / Wireframe).
5. **Validate** — `MODEL_MISSING` should clear after import.

## Milestones

### Milestone 1 — Foundation (in progress)

1. Application shell and project workspace (create/open/save) — **done** (`RspsItemStudio.App` WPF shell)
2. 3D viewport with load, camera, lighting, inspection — **done** (Veldrid `ViewportHost`, orbit/pan/zoom, display modes)
3. Import at least OBJ into studio mesh — **done** (Import OBJ → `inventory.mesh.json` + viewport preview)
4. Item project structure on disk (model, texture, color, animation, effect, stats sections)
5. Basic item-stat editor — **done** (Stats tab, two-way binding)
6. Validation report for missing/invalid project data — **done** (Validate + `validation/last-report.json`)
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
