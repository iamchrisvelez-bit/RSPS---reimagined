# Milestone 2 — OpenRune Definition Path Implementation Plan

> **For agentic workers:** Continue from this plan after M1. Prefer TDD and honest adapter claims.

**Goal:** Stage OpenRune-compatible item definition artifacts (Pack Items TOML + partial OSRS opcode binary) from Item Studio projects without inventing full JS5 cache packs or model codecs.

**Architecture:** Map `ItemDefinitionDocument` (+ `extensions`) through `OsrsItemDefinitionBinary` (OpenRune `ItemCodec` subset) and `OpenRuneItemTomlExporter` (FileStore Pack-Items wiki). `PackToStaging` writes files under `export/staging/openrune-items/`.

**Tech Stack:** Existing .NET 8 adapter projects; no OpenRune JVM dependency in-process.

## Global Constraints

- Never invent unverified opcodes or model/cache bytes
- Live `PackToLiveTree` remains Fail until backup-on-write ships
- Document supported opcodes and wearPos mapping in `COMPATIBILITY.md`
- Prefer OpenRune FileStore Pack Items TOML as the primary integration path

## Delivered in this iteration

1. HWND mouse forwarding for Veldrid viewport (M1 leftover)
2. Partial OSRS item definition encode/decode (opcodes 1,2,3,11,12,13,15,16,23,25,75 + terminator 0)
3. OpenRune Pack Items TOML exporter
4. Staging pack writes TOML + `.obj.bin` when `ExportPreset.ItemId` is set
5. Tests + docs/roadmap updates

## Remaining M2 work

- Confirm wearPos / weight units against a pinned OpenRune revision fixture
- Model codec (inventory/equip) once formats verified
- Optional: invoke or document exact Gradle `packConfig(PackMode.ITEMS, …)` snippet from the user's OpenRune checkout
- Backup-on-write live cache path (still blocked)
