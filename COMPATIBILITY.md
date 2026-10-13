# RSPS Item Studio — Compatibility

Honest support matrix and integration notes. **OpenRune-first**; other revisions via pluggable adapters.

## Primary target

| Target | Status | Notes |
|--------|--------|-------|
| **OpenRune / OpenRune-Server** | Primary; partial in M1 | OSRS-protocol server; first concrete adapter |
| **Rev317** | Stub only | Planned behind same abstractions (Milestone 6) |

## Adapter capability status

| Adapter ID | Model codec | Definition codec | Animation codec | Staging pack | Live cache write |
|------------|-------------|------------------|-----------------|--------------|------------------|
| `openrune` | NotSupported | **Partial** (M2) | NotSupported | TOML + `.obj.bin` when `ItemId` set | Disabled (`Fail`) |
| `rev317` | NotSupported | NotSupported | NotSupported | Success (skipped report, empty staging folder) | Disabled (`Fail`) |

### OpenRune definition support (M2 partial)

Aligned with OpenRune FileStore `ItemCodec` / Pack Items wiki for a **subset** of fields:

| Studio field | TOML (`Pack Items`) | OSRS opcode |
|--------------|---------------------|-------------|
| Name | `name` | 2 |
| Examine | `description` | 3 |
| Stackable | `stacks` | 11 |
| Cost (`extensions.cost`) | `cost` | 12 |
| Equipment slot | `wearPos1` | 13 |
| Not tradeable | `isTradeable=false` | 15 |
| Members | `members` | 16 |
| Inventory model (`extensions.inventoryModel`) | `inventoryModel` | 1 |
| Male/female model0 (+offsets) | `maleModel0` / `femaleModel0` | 23 / 25 |
| Weight | `weight` (game units) | 75 (`weightKg * 1000` unless `extensions.weightUnits`) |

**Not packed yet:** full JS5 archive, models, animations, colour/texture opcodes, notes/placeholders, interface options, params (249), extended 32-bit model opcodes.

**Integration:** set `export/presets.json` → `itemId`, run **Export staging**, copy `export/staging/openrune-items/*.toml` into an OpenRune `itemDirectory`, then `packConfig(PackMode.ITEMS, …)` via OpenRune FileStore tools.

Live tree writes remain blocked until backup-on-write ships.

We do not invent cache, model, or animation behavior. Unverified capabilities surface as explicit `NotSupported` on adapter interfaces.

## OpenRune integration (M1)

- Adapter skeleton and interfaces only until formats are verified against real data.
- Default export is **staging folder + integration report**, not silent writes to live cache or server trees.
- The WPF app exposes **Export staging** only; it validates the project, calls `openrune` `PackToStaging`, writes `export/last-integration-report.json`, and shows entries on the Validation tab. **`PackToLiveTree` is not reachable from the UI.**
- Live cache/server writes require user confirmation and timestamped backup of overwritten files (future Milestone 2+).

## Known limits (Milestone 1)

- Full OpenRune cache packing is **not** claimed complete.
- Animation and effect export are not implemented until codecs are verified.
- Model byte export is adapter-only, never a silent viewport side effect.
- **Viewport (Windows):** M1 requires a manual smoke pass on Windows (`PROJECT_ROADMAP.md` Tasks 8–10). Linux CI compiles rendering sources only; no GPU/HWND runtime there.
- **Viewport input:** `ViewportHost` forwards Win32 mouse messages (`WM_*BUTTON*`, `WM_MOUSEMOVE`, `WM_MOUSEWHEEL`) from the Veldrid child HWND into orbit/pan/zoom. Display mode remains in the left tool strip (not over the HWND). Windows smoke still required.
- Color/recolor editor is a on-disk stub only; UI deferred to Milestone 3.

## Open unknowns

Track and resolve before claiming full export compatibility:

1. **Exact pinned OpenRune cache revision** in production (OpenRune docs often cite ~239; confirm at integration time).
2. **Which OpenRune item fields** are cache-resident vs server plugin/config.
3. **Animation and model byte layouts** for the pinned revision (research against OpenRune-FileStore and real cache fixtures).
4. **Whether male/female equip models and inventory models** are mandatory for all item types in their content pipeline.

Until these are resolved, adapters expose interfaces and partial implementations only. Update this document as verification completes.

## Build platform notes

| Component | Linux (CI / cloud agents) | Windows |
|-----------|---------------------------|---------|
| Core, Definitions, Modeling, Validation, Adapters, Tests | `dotnet test` | Same |
| `RspsItemStudio.Rendering` (Veldrid, `net8.0-windows`) | **Compiles** on Linux CI (no GPU / Win32 HWND at runtime) | Full D3D11 viewport on Windows |
| `RspsItemStudio.App` (WPF + Veldrid host, `net8.0-windows`) | **Not buildable** — SDK lacks `Microsoft.NET.Sdk.WindowsDesktop` | `dotnet build src/RspsItemStudio.App/RspsItemStudio.App.csproj` and `dotnet run --project src/RspsItemStudio.App` |

The WPF shell and Veldrid viewport sources are maintained in-repo; verify import + 3D preview on a Windows machine with the .NET 8 SDK (desktop workload included by default on Windows). `VeldridViewportController.Attach` uses a Win32 child HWND and D3D11 swapchain — runtime requires Windows.
