# RSPS Item Studio — Project Roadmap

Living milestone tracker. Update status as work lands.

## Current status

**Milestone 1 — Foundation:** library + wiring **landed** (including HWND mouse forwarding); **Windows UI smoke is required** before calling M1 fully closed.

**Milestone 2 — OpenRune definitions (in progress):** partial item-definition codec + Pack Items TOML staging. Models/JS5 live pack still pending.

Next step: Windows smoke (M1 checklists) + set `ItemId` on an export preset and verify staged TOML packs with OpenRune FileStore.

### Linux / CI verification (M1)

- `dotnet test` — Core, Modeling, Definitions, Validation, Adapters, Rendering (compile), Tests
- Living docs: `PROJECT_ROADMAP.md`, `ARCHITECTURE.md`, `COMPATIBILITY.md`
- No UI command for live cache pack (`PackToLiveTree`); staging export only via **Export staging**

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
4. Orbit (left drag), pan (right drag), zoom (wheel); switch **Display mode** in the left tool strip (Solid / SolidUntextured / Wireframe).
5. **Validate** — `MODEL_MISSING` should clear after import.

### Windows manual check — staging export (Task 10)

1. With a valid project (name set, inventory mesh imported), click **Export staging**.
2. Validation runs first; fix any errors and retry.
3. Validation tab shows OpenRune **skipped / not packed** integration entries; status bar shows report summary.
4. Confirm `export/staging` (or preset folder) and `export/last-integration-report.json` under the project.
5. Confirm there is **no** menu or button for live cache / server tree export.

## Milestones

### Milestone 1 — Foundation (in progress — Windows smoke pending)

1. Application shell and project workspace (create/open/save) — **done** (`RspsItemStudio.App` WPF shell)
2. 3D viewport with load, camera, basic lighting — **done** (Veldrid `ViewportHost`, orbit/pan/zoom, display modes). **Not in M1:** mesh inspection overlay, debug primitives, TRS/`MeshTransform` editor.
3. Import at least OBJ into studio mesh — **done** (Import OBJ → `inventory.mesh.json` + viewport preview)
4. Item project **folder layout** on disk (models, materials, colors stub, animations/effects placeholders, stats) — **done**. **Not in M1:** color/recolor editor (deferred to **M3**), animation/effects authoring UI.
5. Basic item-stat editor — **done** (Stats tab, two-way binding)
6. Validation report for missing/invalid project data — **done** (Validate + `validation/last-report.json`)
7. Adapter interfaces + OpenRune adapter skeleton (no fake full export) — **done** (staging pack + honest skipped report)
8. Seed `PROJECT_ROADMAP.md`, `ARCHITECTURE.md`, `COMPATIBILITY.md` — **done**

**Not in M1 (planned later):** undo/redo stack, `RspsItemStudio.Animation` / `RspsItemStudio.Effects` projects, mesh TRS transforms.

**Success criteria:** create project → import OBJ → edit stats → validate → export staging shows clear adapter “not yet implemented” path without corrupting any game files. **Required:** verify end-to-end on Windows (see checklists above).

### Milestone 2 — OpenRune definition + model path (in progress)

- [x] Partial OSRS item-definition encode/decode (OpenRune `ItemCodec` subset)
- [x] OpenRune Pack Items TOML staging under `export/staging/openrune-items/`
- [x] Integration report lists written TOML/bin + skipped model/anim/cache
- [ ] Confirm wearPos/weight against a pinned OpenRune revision fixture
- [ ] Model codec as formats are confirmed
- [ ] Backup-on-write into user-selected cache/server paths

See `docs/superpowers/plans/2026-10-13-milestone-2-openrune-definitions.md`.

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
