# RSPS equipment redesigns (B01–B14)

There are 84 low-poly items built from `reference_sheet.jpg` (14 batches × 6, read left→right, top→bottom).
They are packaged as game-ready RuneScape classic-format models, 36×32 inventory sprites and item definitions.

**Integrating into the server? Read [HANDOFF.md](HANDOFF.md).**

```sh
pip install -r requirements.txt
./verify.sh                      # build out/ + run all checks (JDK optional, enables the RuneLite check)
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
| `build.py` | Builds `out/` (models, sprites, defs, manifest) |
| `tests/` | Release checks |
| `verify/` | RuneLite `ModelLoader` sources (BSD-2, unmodified apart from removing Lombok) + cross-check harness |

## Interpretations of the sheet
- B04 shows one armour suit three times. It is split into Reaver platebody, Reaver platelegs and Reaver warboots.
- The B07 hooded tunics are body-slot items with the hood built in, so they hide the hair.
