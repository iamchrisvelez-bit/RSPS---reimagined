# RSPS Item Studio — Architecture

High-level module layout and data flow. See the design spec for full detail.

## Principles

- **Author once, adapt per revision.** The item project is revision-neutral; adapters map project data to client/server formats.
- **Modular boundaries.** Rendering, modeling, animation, effects, definitions, validation, and I/O are separate projects.
- **Safety first.** No writes into live client cache, server trees, or existing definitions without explicit confirmation and automatic backup.
- **Incremental delivery.** Ship working foundations and honest adapter contracts; avoid fake full export.

## Solution modules

| Module | Responsibility |
|--------|----------------|
| `RspsItemStudio.App` | WPF shell, panels, commands, dialogs |
| `RspsItemStudio.Core` | Item project model, schema versioning, shared JSON (`StudioJson`); undo stack **planned** |
| `RspsItemStudio.Rendering` | 3D viewport, camera, basic lighting (M1); inspection overlay **planned** |
| `RspsItemStudio.Modeling` | Mesh import, studio mesh JSON (M1); `MeshTransform` / TRS editing **planned** |
| `RspsItemStudio.Animation` | **Planned** — clip binding and preview APIs (not in solution yet) |
| `RspsItemStudio.Effects` | **Planned** — effect attachment model and triggers (not in solution yet) |
| `RspsItemStudio.Definitions` | Item stats/flags editor model |
| `RspsItemStudio.Validation` | Validation engine and reports |
| `RspsItemStudio.Adapters.Abstractions` | Codec/packer/preview interfaces |
| `RspsItemStudio.Adapters.OpenRune` | First real adapter (partial until verified) |
| `RspsItemStudio.Adapters.Rev317` | Future stub adapter |
| `RspsItemStudio.Tests` | Unit and fixture tests |

## Data flow

1. User edits an **item project** (folder on disk: `itemstudio.json`, `meta/item.json`, models, materials, etc.).
2. **Core** loads/saves project documents via `StudioJson` (camelCase, indented, null omission, camelCase enums).
3. **Validation** runs against project state; errors block export.
4. **Adapters** implement codecs and packers to map studio data to revision-specific bytes and layouts; unimplemented paths return explicit `NotSupported` (never silent success).

## Adapter contracts

- `IModelCodec` — studio mesh ↔ revision model bytes
- `IAnimationCodec` — studio/bindings ↔ revision animation data
- `IDefinitionCodec` — `meta/item.json` ↔ revision item definition encoding
- `ICachePacker` — pack staged files into cache/server layout
- `IRevisionPreview` — revision-accurate preview hints when available

## Item project layout (on disk)

One folder per item project; portable and version-control friendly. Key paths include `itemstudio.json`, `meta/item.json`, `models/`, `materials/`, `colors/recolor.json`, `animations/`, `effects/`, `export/presets.json`, and `validation/last-report.json`.
