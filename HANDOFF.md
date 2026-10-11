# Handoff: adding the 84 redesigned items to the game

This file is for whoever integrates the assets (person or agent). Follow the steps in order.
Everything you need is in `out/`. The single source of truth is `out/manifest.json`.

## 0. Verify the package before touching the server
```sh
pip install -r requirements.txt
./verify.sh            # rebuilds out/ from source + all checks; must end with "OK"
```
If the cache already uses model ids 60000–60167 or item ids 30000–30083, rebuild with free ranges.
**Don't hand-edit ids anywhere**: the manifest, definitions and file names are all regenerated together.
```sh
./verify.sh --base-model-id <first free model id> --base-item-id <first free item id>
```
Constraints:
- Model ids must stay ≤ 65535. Item definitions store model ids as unsigned 16-bit.
- The model ids for one build are a contiguous block of 168.

## 1. What is in `out/`
| Path | Use |
|---|---|
| `manifest.json` | One entry per item: `item_id`, `name`, `slot`, `equip_slot`, `inventory_model`, `worn_model`, `icon` (zoom2d/xan2d/yan2d), `hide_kits`, `action`, file paths and sha1s |
| `models/<id>.dat` | Raw RS model, classic format: HSL colours, smooth (Gouraud) shading = render type 0, per-face priorities 10 (surface) and 11 (detail lines drawn on top). No textures, alpha or skins |
| `models/<id>.gz` | The same bytes gzipped. 317 caches store models this way |
| `sprites/<item_id>.png` | 36×32 RGBA inventory icon in client style (outline 0x000001, shadow 0x302020) |
| `defs/osrs_item_definitions.json` | Item definitions using RuneLite `ItemDefinition` field names |
| `defs/ItemDef317_snippet.java` | `switch (id)` block for a 317 client's `ItemDef.forID` |
| `defs/equipment.json` | Server-side equip slot, hidden kit parts, two-handed flag |
| `defs/requirements.json` | Proposed equip requirements per item (skill name, OSRS skill id, level); edit `rsgen/requirements.py` and rebuild to change them |
| `obj/` | OBJ/MTL of each worn model, for Blender or a model editor |
| `renders/`, `sheets/` | Previews only |

Each item has **two models**:
- `inventory_model` is centred on the origin. Use it for the icon and the ground item.
- `worn_model` is positioned on the player. Use it for `maleModel0` and `femaleModel0`.

## 2. Pack the models into the cache
Pick the section that matches the server's revision. Look for the cache folder (`main_file_cache.dat2` + `.idx*` = OSRS-style; `main_file_cache.dat` + `idx0..4` = 317-style).

**OSRS-style cache (dat2):** for every model id, write the raw `.dat` bytes to **index 7, archive = model id, file 0**. Use the server's existing cache tool (RuneLite `cache` library `Store`, Displee `CacheLibrary`, OpenRS2 tools, or the base's own packer). Let the tool handle container compression and the reference table. Never append to `.dat2` by hand.

**317-style cache:** for every model id, write the **`.gz`** bytes to **index 1 (models), file id = model id**, using the base's cache packer. Some 317 bases load models from a folder or "custom models" loader instead. If yours does, copy `models/<id>.gz` there.

## 3. Add the item definitions
**OSRS-style:** for each entry in `defs/osrs_item_definitions.json`:
1. Create item `id` in **config index 2, archive 10** (or the base's JSON/TOML item definitions).
2. Set the fields that are listed.
3. Raise the base's total-items count if it has one.

**317-style:**
1. Paste the cases from `defs/ItemDef317_snippet.java` into `ItemDef.forID`, after the item is decoded.
2. Rename the fields to match the base. Common aliases:
   - `modelID` = `inventoryModel` / `modelId`
   - `modelZoom` = `zoom2d`
   - `modelRotation1` = `rotationY` / `xan2d`
   - `modelRotation2` = `rotationX` / `yan2d`
   - `maleEquip1` = `maleWield` / `maleModel`
   - `actions` = `itemActions`
3. Raise `totalItems` if the new ids exceed it.

**Server side (both):**
- Register each item's equip slot and two-handed flag from `defs/equipment.json` wherever the server keeps equipment data.
- Slot numbers: 0 head, 1 cape, 2 neck, 3 weapon, 4 body, 5 shield, 7 legs, 9 hands, 10 feet.
- `hide_kits` are player kit parts to hide while worn: 6 arms, 8 hair, 11 jaw.
  - Most platebodies are **short-sleeved** cuirasses, so they hide nothing: the player's own arms show and animate below the pauldrons.
  - Long-sleeved bodies (robes, ranger tunics, solar scale body) hide arms. The hooded tunics also hide hair and jaw. On OSRS-style defs these are `wearPos2`/`wearPos3`. Bases without that field usually hard-code them in an "is full body / full helm / full mask" list: add these ids there.

## 4. Sprites
OSRS-style and 317 clients **render inventory icons from `inventory_model` at runtime**, so the cache doesn't need the PNGs. Use `sprites/<item_id>.png` where the server or website needs a static icon: item DB, shops, wiki, Discord bot. Only put them in the sprite archive if the base has a custom-icon override system.

## 5. In-game acceptance test
For each `item_id`:
1. Spawn it (`::item <id>`).
2. Check the icon looks like `sprites/<id>.png`. If it is cropped or tiny, adjust only `zoom2d` (bigger number = smaller icon).
3. Drop it: the ground model shows.
4. Equip it: it appears on the player, in the right slot, with the right parts hidden.

## 6. Where the models come from
`out/` is built from **`pipeline_models/`**: the models refined from the design sheet by `pipeline/refine_to_match.py` (see PIPELINE.md). `build.py` fits each one onto the player for its slot. Capes are turned so the artwork faces away from the wearer. The surface carries the design's own colours, shadows and texture, and thin painted lines (glow cracks, trims, straps) are separate strips with face priority 11 so they draw over the surface.

The earlier procedural models are still available: `./verify.sh --source handbuilt` packages them instead (flat shading, single priority 10). Model and item ids are the same either way.

## 7. Known limitations, stated plainly
- **No vertex skins.** Worn models are placed on a ~200-unit-tall player (feet at y=0, facing +z in authoring space, stored as RS y-down). They show correctly while standing but will **not bend with animations** until vertex groups are copied from the base player kit in a model editor.
- Items with `worn_placement: item_space_needs_offset` (weapons, shields, amulets) have the grip or centre at the origin. They need the base's usual hand/neck offset, or re-posing, before they look right when equipped.
- Every model has at most 2,400 faces (the tests enforce ≤3,000), so equipped players stay cheap to draw.
- Models are reliefs built from one front view of each design: the back is a simpler, slightly darker version of the front, and depth comes from the design's shading rather than a full 3D sculpt.
- Detail lines are at least ~1.8 RS units wide so they stay continuous on the integer vertex grid. Weapons are too small for that, so they carry their detail in the face colours only.
- `icon.zoom2d` is estimated from model size (≈12.5 × largest extent). Expect small per-item tweaks.
- These were verified offline:
  - all 168 models decode byte-for-byte identically with RuneLite's own `ModelLoader` (`verify/runelite_check.py`)
  - geometry, colours and the 36×32 sprites pass the test suite

  They have **not** yet been loaded in this server's client. Step 5 is the real test.
