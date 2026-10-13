# Swapping the redesigns into real OSRS items (rev 241)

`out/` packages the 84 redesigns as **new items** with fresh ids. This kit does the other job: it makes
each redesign a drop-in replacement for an **existing** item's look, so the client shows our model with
the existing item's animations, placement and icon framing:

```sh
# a RuneLite flatcache dump of the game cache at the server's revision (indexes 0, 1, 2 and 7),
# e.g. git clone --depth 1 https://github.com/abextm/osrs-cache   (tag 2026-10-07-rev241)
python3 tools/swap_build.py  --cache <cache dump>      # -> out_swap/models/*.dat + out_swap/swaps.json
python3 tools/swap_verify.py --cache <cache dump>      # -> out_swap/verify.json + out_swap/verify/<code>.png
python3 tools/check_ids.py   --cache <SERVER cache dump>   # our ids must be free in the server's cache
```

## What was checked against the real game data (rev 241)

The checks use real item definitions, models, player kits, the player skeleton and animation frames,
read straight from the cache. They run through RuneLite's own decoders and its port of the client's
sprite renderer. The animation maths and the player-model merge are ported from the client
(`tools/osrs/`).

| Finding | Consequence | Handled by |
|---|---|---|
| Rev 241 already uses model ids up to **62050** and item ids up to **34645**; our old package ids (models 60000–60167, items 30000–30083) **all collided** | Packing them would have overwritten real game models and items | `build.py` now defaults to models 63000+, items 40000+. Swap models start at 64000. `tools/check_ids.py` checks any server cache |
| Every real worn model carries **vertex groups** (labels the player skeleton animates); ours had none | A worn item would stay rigid while the player walks or attacks | Each vertex takes the label of the nearest original vertex |
| Worn models are **placed on the player**. Weapons and shields sit in the hand, already rotated | Our weapons were centred on the origin | Weapons and shields are aligned rigidly to the original (principal axes; the orientation is picked by surface distance, so heads land on heads). Armour is fitted to the body volume the original covered |
| Some items are **split over several models** (a platebody is torso + arms) | Item definitions expect the same model slots | Our model is split the same way, face by face |
| The client finds every **rotation centre** by averaging all vertices with the centre's labels across the merged player model, item included | Our models have many more vertices than the originals, so they pulled centres off. Up to 12 units of body drift measured on the rune platebody | Our vertices move to a label that the skeleton moves identically (same skeleton class) but that the original doesn't use. The original's own labelled vertices are kept as invisible anchors on zero-area faces |
| The client merges player models **through faces**, dropping unused vertices and sharing identical positions (deobfuscated `ModelData(ModelData[], int)`) | Anchors must be on faces. Merged vertices keep the first model's label | Anchors use zero-area faces (kept by the merge, never drawn). The verifier reproduces the client merge exactly |
| **Face priorities** decide what draws over what in the merged player model | | Each face takes the priority of the nearest original face. Detail lines go one higher, up to 11 |
| **Inventory models** are the worn model re-posed for the icon camera | Our icon could lie the wrong way | We apply the template's own worn-to-inventory transform. Then both icons are rendered with the item's zoom2d/xan2d/yan2d by the client's sprite code, and ours is rescaled to the same footprint |
| OSRS **reuses one model for many items** (every platebody tier is the same model, recoloured) | Overwriting a model in place would restyle every tier | Swapped models get new ids. Each swap lists the item-definition fields to set: model slots, plus recolour/retexture lists cleared |

## Results (all 84 redesigns, male and female bodies, idle/walk/run/slash poses)

`out_swap/verify.json` has the numbers for each item. `out_swap/verify/<code>.png` shows the original and
ours, posed by the game's animations, with both inventory icons rendered by the client's code.
- **body drift**: how far the player's own body moves differently wearing ours instead of the original.
- **follow**: how far our item lands from where the original outfit's rotation centres would put it.

Both are in RS units (a player is about 200 tall). Current run (rev 241):

| | Swaps (`out_swap/`) | New items (`out/`) |
|---|---|---|
| Items checked | 84 | 84 |
| Body drift, median / max | **0.00** / 6.1 | **0.00** / 6.1 |
| Items within 2 units | 76 | 75 |
| Follow, items within 2 units | 80 | 79 |
| Icon silhouette overlap with the template, median | 0.67 | 0.67 |

- **Body armour and weapons are exact.** Every platebody, helm, weapon, shield and cape lands at 0–1 units: integer rounding in the client's own maths.
- **Leg armour and skirts drift up to 6 units.** Their skeleton classes leave no free twin label, so our vertices have to share labels with the original's rotation centres.
- **Icon overlap stays below 1 by design.** The redesigns have different shapes from their templates. The footprint (largest side of the icon) is matched.
- `out_swap/VERIFY_SAMPLES.png` shows six slots side by side.

Not checked here: other skeletons (non-player), newer skeletal ("animaya") animations, and recolour-based variants. Nothing replaces the in-game test (HANDOFF.md step 5).

## Applying a swap on the server

For each entry in `out_swap/swaps.json`:
1. Pack every `out_swap/models/<id>.dat` into the cache (index 7, archive = id), as in HANDOFF.md step 2.
   Check the ids first with `tools/check_ids.py`.
2. Edit the template item's definition with the fields in `item_def_patch`:
   - `inventoryModel`, `maleModel0/1/2` and `femaleModel0/1/2` get our new ids (−1 removes a slot)
   - empty `colorFind/colorReplace/textureFind/textureReplace`, so the template's recolours don't hit
     our colours

   Names, stats, requirements and zoom2d/xan2d/yan2d stay as they are.
3. Restart the client fully, since item definitions are cached.

Chat-head models (`maleHeadModel`, used by helms in dialogue) are not replaced. Dialogue heads keep the
original helm.
