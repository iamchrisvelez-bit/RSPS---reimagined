# RSPS Item Studio — Design Spec

**Date:** 2026-10-13  
**Status:** Draft for user review  
**Product working title:** RSPS Item Studio (repo: RSPS---reimagined)

## 1. Goal

Build a Windows desktop content-creation suite for authoring custom RuneScape private-server items end-to-end: model/import, materials and recolors, animations, effects, gameplay definitions, validation, and revision-specific export.

This is a professional authoring tool, not a model viewer.

## 2. Decisions locked

| Decision | Choice | Notes |
|----------|--------|-------|
| Primary server target | **OpenRune / OpenRune-Server** | OSRS-protocol server (RSMod/Alter lineage); not classic 317 |
| First concrete adapter | OpenRune (OSRS cache/defs via OpenRune-FileStore concepts; target revision ~239 as documented by OpenRune unless user pin changes) | |
| Multi-revision strategy | Shared authoring core + pluggable import/export/preview adapters | 317 and others are stubbed until implemented |
| Desktop platform | Windows only (Milestone 1+) | |
| Tech stack | .NET 8, WPF shell, **Veldrid** for 3D (Silk.NET only if Veldrid blocks M1), xUnit tests | Approach 1 — approved |
| Compatibility honesty | Never invent cache/model/anim behavior | Unverified capabilities = explicit `NotSupported` + adapter interface |

## 3. Architecture

### 3.1 Principles

- **Author once, adapt per revision.** The item project is revision-neutral. Adapters map project data to client/server formats.
- **Modular boundaries.** Rendering, modeling, animation, effects, definitions, validation, and I/O are separate projects.
- **Safety first.** No writes into live client cache, server trees, or existing definitions without explicit confirmation and automatic backup.
- **Incremental delivery.** Milestone 1 ships a working foundation and honest adapter contracts, not fake full OpenRune export.

### 3.2 Solution modules

| Module | Responsibility |
|--------|----------------|
| `RspsItemStudio.App` | WPF shell, panels, commands, dialogs |
| `RspsItemStudio.Core` | Item project model, undo stack, schema versioning |
| `RspsItemStudio.Rendering` | 3D viewport, camera, lighting, inspection |
| `RspsItemStudio.Modeling` | Mesh import/transform, studio mesh format |
| `RspsItemStudio.Animation` | Clip binding and preview APIs |
| `RspsItemStudio.Effects` | Effect attachment model and triggers |
| `RspsItemStudio.Definitions` | Item stats/flags editor model |
| `RspsItemStudio.Validation` | Validation engine and reports |
| `RspsItemStudio.Adapters.Abstractions` | Codec/packer/preview interfaces |
| `RspsItemStudio.Adapters.OpenRune` | First real adapter (partial until verified) |
| `RspsItemStudio.Adapters.Rev317` | Future stub adapter |
| `RspsItemStudio.Tests` | Unit and fixture tests |

### 3.3 Adapter contracts

Adapters implement clearly separated interfaces (names indicative):

- `IModelCodec` — studio mesh ↔ revision model bytes
- `IAnimationCodec` — studio/bindings ↔ revision animation data
- `IDefinitionCodec` — `meta/item.json` ↔ revision item definition encoding
- `ICachePacker` — pack staged files into cache/server layout
- `IRevisionPreview` — revision-accurate preview hints (palette, equip pose) when available

Unimplemented members must throw or return typed `NotSupported` results with user-visible messages. No silent no-ops that look like success.

## 4. Item project format

One folder per item project (portable, version-control friendly):

```
MyCustomScimitar/
  itemstudio.json
  meta/item.json
  models/
    inventory.mesh.json
    equipped_male.mesh.json
    equipped_female.mesh.json
    source/                    # original imports (preserved)
  materials/
    textures/
    materials.json
  colors/recolor.json
  animations/
    bindings.json
    clips/
  effects/effects.json
  export/presets.json
  validation/last-report.json
```

### 4.1 Identity rules

- Studio entities use stable internal GUIDs.
- Game item IDs are assigned in **export presets per adapter**, so one project can target multiple servers/revisions without rewriting core data.
- `itemstudio.json` carries schema version for migrations.

### 4.2 Definition model (`meta/item.json`)

Milestone 1 fields:

- Name, examine text
- Equipment slot
- Attack and defense bonuses
- Strength, ranged, magic, prayer bonuses
- Level requirements
- Weight
- Flags: tradeable, stackable, noted, and other common flags as first-class fields when clearly shared
- `extensions` map for OpenRune-/revision-specific fields without inventing opcodes

### 4.3 Colors

- Primary / secondary / detail (and additional slots as needed)
- Store both preview RGB and Jagex-style packed HSL where applicable
- Preset palettes supported in the color document

## 5. Viewport and modeling (Milestone 1)

### 5.1 Viewport

- Orbit, pan, zoom
- Grid, basic lighting
- Display modes: textured shaded, untextured shaded, wireframe
- Mesh inspection: vertex/triangle counts, bounds, material slots
- Hooks for animation and effect playback (interfaces only until data exists)

### 5.2 Import

- Required: **OBJ**
- Preferred if schedule allows in M1: **glTF / glb**
- Pipeline: import → normalize (coordinate/scale helpers) → `StudioMesh` under `models/` → copy original into `models/source/`
- Incomplete mappings (missing UVs/materials) produce validation warnings; preview shows retained data only

### 5.3 Editing scope in M1

- Translate / rotate / scale
- Simple primitives (cube/plane) for smoke tests
- Vertex-level sculpting deferred

Cache/model byte export is **adapter-only**, never a silent viewport side effect.

## 6. Animation and effects

### 6.1 Target capability (product)

- Assign, preview, edit, and export animations where the revision supports them
- Equip, idle, attack, special-attack, and custom sequences when supported
- Effects: particles, glows, trails, auras, projectiles, hit effects, sound hooks, timed triggers
- Attach effects to animation frames, equip states, combat actions, or item interactions

### 6.2 Milestone 1 honesty

- Persist empty/structured `animations/bindings.json` and `effects/effects.json`
- UI may show read-only placeholders listing intended binding slots
- No claim of OpenRune animation/effect export until codecs are verified against real formats

## 7. Validation and export safety

### 7.1 Validation

Runnable at any time; **errors block export**.

Checks (M1 baseline):

- Missing or unloadable models
- Empty/invalid name
- Broken texture references
- Out-of-range stats
- Equipable items missing slot
- Duplicate item IDs within an export preset
- Adapter capability gaps (e.g. animation export not implemented)

Outputs: in-app report and `validation/last-report.json`.

### 7.2 Export safety

- Default export writes to a **staging folder** plus an **integration report** (what was created/changed and where it must be placed)
- Writing into a live cache or server directory requires:
  1. Explicit user confirmation
  2. Timestamped backup of files that would be overwritten
- Never overwrite without confirmation
- Destructive project operations use undo where practical; filesystem game-tree writes always backup-first

## 8. Documentation set (repo)

Maintain living docs (created with implementation; seeded from this spec):

- `PROJECT_ROADMAP.md` — milestones, status, next step
- `ARCHITECTURE.md` — modules, data flow, adapter model
- `COMPATIBILITY.md` — supported revisions, known limits, unknowns, integration steps for OpenRune

## 9. Testing strategy

- Unit tests: project serialize/deserialize, definition validation, color conversion, animation binding map integrity, export staging logic, adapter registration
- Integration/fixtures: sample OpenRune-compatible files **only when real fixtures are available**; do not synthesize fake “valid” cache bytes to pretend compatibility
- CI-friendly headless tests for Core / Validation / Definitions; GUI/viewport tests may be manual or limited in M1

## 10. Milestone plan (high level)

### Milestone 1 — Foundation (first implementation plan)

1. Application shell and project workspace (create/open/save)
2. 3D viewport with load, camera, lighting, inspection
3. Import at least OBJ into studio mesh
4. Item project structure on disk (model, texture, color, animation, effect, stats sections)
5. Basic item-stat editor
6. Validation report for missing/invalid project data
7. Adapter interfaces + OpenRune adapter skeleton (no fake full export)
8. Seed `PROJECT_ROADMAP.md`, `ARCHITECTURE.md`, `COMPATIBILITY.md`

**M1 success criteria:** create project → import OBJ → edit stats/colors stubs → validate → see clear adapter “not yet implemented” export path without corrupting any game files.

### Milestone 2 — OpenRune definition + model path (planned)

- Verify OpenRune-FileStore / OSRS item definition and model formats against real data
- Implement definition codec + staging export + integration report
- Model codec as formats are confirmed
- Backup-on-write into user-selected cache/server paths

### Milestone 3 — Materials, recolor, richer preview

- Texture pipeline, transparency, palette/recolor live preview
- Stronger material editor and UV inspection

### Milestone 4 — Animation bindings and preview

- Wire idle/attack/special/equip bindings to verified revision data
- Playback in viewport where formats allow

### Milestone 5 — Effects editor

- Frame/action-triggered effects; preview subset; export where supported

### Milestone 6 — Additional revision adapters

- Implement Rev317 (and others) behind the same abstractions
- Cross-revision project reuse where formats allow

## 11. Explicit non-goals for Milestone 1

- Full OpenRune cache packing claimed as complete
- Blender-grade mesh sculpting
- Multi-OS builds
- Silent modification of any client/server files
- Invented opcode-level definition writers without format verification

## 12. Open unknowns (tracked in COMPATIBILITY.md)

- Exact pinned OpenRune cache revision the user runs in production (docs show ~239; confirm at integration time)
- Which OpenRune item fields are cache-resident vs server plugin/config
- Animation and model byte layouts for the pinned revision (research against OpenRune-FileStore / cache fixtures)
- Whether male/female equip models and inventory models are mandatory for all item types in their content pipeline

Until unknowns are resolved, adapters expose interfaces and partial implementations only.

## 13. User workflow (product)

1. Create or import an item project  
2. Import/create/modify 3D model  
3. Apply textures, colors, materials  
4. Assign or create animations  
5. Add effects and timing  
6. Configure stats, requirements, equipment behavior  
7. Preview in viewport (anim + effects when available)  
8. Validate  
9. Export via selected adapter to staging (or confirmed live path with backup)  
10. Read integration report for placement instructions  

Milestone 1 covers steps 1–3 (basic), 6–8, and an honest partial 9–10.
