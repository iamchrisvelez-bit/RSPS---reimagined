# RSPS Item Studio — Compatibility

Honest support matrix and integration notes. **OpenRune-first**; other revisions via pluggable adapters.

## Primary target

| Target | Status | Notes |
|--------|--------|-------|
| **OpenRune / OpenRune-Server** | Primary; partial in M1 | OSRS-protocol server; first concrete adapter |
| **Rev317** | Stub only | Planned behind same abstractions (Milestone 6) |

## Adapter capability status (M1)

| Adapter ID | Model codec | Definition codec | Animation codec | Staging pack | Live cache write |
|------------|-------------|------------------|-----------------|--------------|------------------|
| `openrune` | NotSupported | NotSupported | NotSupported | Success (skipped report, empty staging folder) | Disabled (`Fail`) |
| `rev317` | NotSupported | NotSupported | NotSupported | Success (skipped report, empty staging folder) | Disabled (`Fail`) |

Codec methods return `AdapterResult.NotSupported` with an explicit message — no fabricated cache or model bytes. Staging export creates the configured folder and an `IntegrationReport` listing skipped steps; live tree writes remain blocked until formats are verified and backup flow ships.

We do not invent cache, model, or animation behavior. Unverified capabilities surface as explicit `NotSupported` on adapter interfaces.

## OpenRune integration (M1)

- Adapter skeleton and interfaces only until formats are verified against real data.
- Default export is **staging folder + integration report**, not silent writes to live cache or server trees.
- Live cache/server writes require user confirmation and timestamped backup of overwritten files.

## Known limits (Milestone 1)

- Full OpenRune cache packing is **not** claimed complete.
- Animation and effect export are not implemented until codecs are verified.
- Model byte export is adapter-only, never a silent viewport side effect.

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
| `RspsItemStudio.App` (WPF, `net8.0-windows`) | **Not buildable** — SDK lacks `Microsoft.NET.Sdk.WindowsDesktop` | `dotnet build src/RspsItemStudio.App/RspsItemStudio.App.csproj` and `dotnet run --project src/RspsItemStudio.App` |

The WPF shell sources are maintained in-repo; verify the app on a Windows machine with the .NET 8 SDK (desktop workload included by default on Windows).
