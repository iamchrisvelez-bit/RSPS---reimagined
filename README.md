# RSPS equipment redesigns (B01–B14)

There are 84 low-poly items built from `reference_sheet.jpg` (14 batches × 6, read left→right, top→bottom).
They are packaged as game-ready RuneScape classic-format models, 36×32 inventory sprites and item definitions.

**Integrating into the server? Read [HANDOFF.md](HANDOFF.md).**
**Automatic sheet → 3D → RS pipeline: see [PIPELINE.md](PIPELINE.md)** (`./run_pipeline.sh`).

```sh
pip install -r requirements.txt
./verify.sh                      # build out/ from pipeline_models/ + run all checks (JDK optional, enables the RuneLite check)
./verify.sh --source handbuilt   # package the procedural models (rsgen/items.py) instead
./verify.sh --base-model-id 61000 --base-item-id 31000   # renumber everything consistently
```

## Layout
| Path | |
|---|---|
| `rsgen/geom.py` | Mesh kit: loft/lathe/sweep/extrude primitives, consistent CCW-outward winding |
| `rsgen/parts.py` | Templates fitted to the standard player: torso, helms, legs, robes, weapons, shields, jewellery |
| `rsgen/items.py` | The 84 item builders (`@item(code, name, slot)`) |
| `rsgen/rsformat.py` | RS classic model encoder/decoder, HSL palette, mesh cleaning, OBJ export |
| `rsgen/render.py` | Preview renderer and inventory-sprite generator |
| `build.py` | Builds `out/` (models, sprites, defs, manifest). Pipeline models are fitted onto real OSRS template items |
| `rsgen/swap.py` | Fitting onto a template item: placement, vertex groups (animation labels), model split, priorities, rotation-centre anchors |
| `rsgen/detail.py` | Detail lines (glow cracks, trims) found in the designs and built as strips |
| `tools/swap_build.py`, `tools/swap_verify.py` | Swap kit: replace existing items' looks, and verify with the game's own animations and icon renderer (SWAP.md) |
| `tools/osrs/` | Read-only OSRS cache access ported from RuneLite: flatcache, item/kit/sequence definitions, frames, client-accurate animation |
| `tools/check_ids.py` | Checks our model and item ids are free in a server's cache |
| `data/osrs-rev241/` | The rev 241 game data these need (template items, their models, player kits, skeleton, four animations): 0.9 MB |
| `tests/` | Release checks |
| `tools/compare.py` | Reference panel vs. current renders, side by side (`out/compare/`) |
| `tools/preview.py` | Quick render of ad-hoc meshes while tuning templates |
| `verify/` | RuneLite cache sources (BSD-2): `ModelLoader`, the item sprite renderer (Lombok removed, minimal `ItemDefinition`), plus `ModelDump`/`IconRender`/`VerifyModels` harnesses |

## Interpretations of the sheet
- B04 shows one armour suit three times. It is split into Reaver platebody, Reaver platelegs and Reaver warboots.
- The B07 hooded tunics are body-slot items with the hood built in, so they hide the hair.
