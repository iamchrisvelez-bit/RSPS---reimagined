# RSPS Item Studio — Compatibility

Honest support matrix and integration notes. **OpenRune-first**; other revisions via pluggable adapters.

## Primary target

| Target | Status | Notes |
|--------|--------|-------|
| **OpenRune / OpenRune-Server** | Primary; partial in M1 | OSRS-protocol server; first concrete adapter |
| **Rev317** | Stub only | Planned behind same abstractions (Milestone 6) |

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
