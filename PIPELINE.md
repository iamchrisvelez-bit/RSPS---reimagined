# Automatic pipeline: design sheet → RS models

Three scripts, each usable on its own:

```sh
./run_pipeline.sh                                   # all three stages, built-in backend
python3 pipeline/stage1_designs_to_3d.py            # sheet  -> pipeline_out/01_views/<code>/
python3 pipeline/stage2_images_to_models.py         # images -> pipeline_out/02_models/<code>/model.obj
python3 pipeline/stage3_models_to_rs.py             # models -> pipeline_out/03_rs/<code>/<id>.dat
```

## Stage 1: designs → 3D images
This stage cuts all 84 items out of `reference_sheet.jpg`. Items are named B01_1…B14_6, in the same order as the sheet. For each item it writes:
- `color.png`: transparent cutout
- `mask.png`: silhouette
- `depth.png`: 16-bit depth map
- `normal.png`: normal map
- `meta.json`: item name and equipment slot

It also writes `CONTACT.png`, an overview sheet.

How the cutting works:
- Items are separated from the dark backdrop by colour, saturation and texture. Soft drop shadows are rejected.
- Items that touch are split by erosion.
- Items made of several pieces, such as a pair of greaves, are joined back together.

The depth is **estimated**, not measured: a rounded profile from the silhouette, plus relief from the artwork's shading.

## Stage 2: 3D images → models
| `--backend` | What it does | Where it runs |
|---|---|---|
| `lowpoly` (default) | Builds low-poly triangles that follow the artwork. Points sit along a traced, simplified outline and along colour borders; a Delaunay triangulation of them is trimmed to the silhouette, and each triangle takes its dominant flat colour. The artwork's baked lighting is mostly removed (`--delight 0.75`) and its colours are reduced to `--colors 8` material tones, so the RS client's lighting does the shading. The front comes from a smoothed depth map, with a thinner mirrored back. About 1,300 faces. | Anywhere (it ran here) |
| `relief` | The older grid version of the above (stair-stepped outline, noisier colour). | Anywhere |
| `command` | Runs your own image-to-3D tool on every item. `--cmd` is a template using `{image} {mask} {depth} {outdir} {code}`, and the tool must write a .glb/.obj/.ply into `{outdir}`. | A machine with that tool, usually a GPU box |
| `meshy` | Sends each stage-1 cutout to Meshy's image-to-3D API and downloads a textured GLB (a real 3D shape). **Paid.** | Here, once the key and network access are set up (below) |
| `import` | Uses meshes you made elsewhere, from `--import-dir/<code>.glb|obj|ply`. Examples: an online image-to-3D service fed with the stage-1 `color.png` files, or Blender. | Anywhere |

**Know the limits.** The `lowpoly` and `relief` backends reconstructs from one front view. It works well for flat items: blades, shields, amulets, capes, bows. Armour and helms come out as a relief, not a full sculpt with a believable back. For true 3D, use an AI image-to-3D tool through `command` or `import`. This environment has no GPU and no access to model downloads, so those backends are written but not exercised here (the tests cover the `import` path's file loading).

## Stage 3: models → RS
This stage takes the stage-2 output, or **any** `.obj`/`.ply`/`.glb` file or folder of them. For each model it:
1. Reorients to the game's axes (`--up`, `--forward`). For a Blender export use `--up z --forward -y`.
2. Fits the model into its equipment slot. Worn slots go on the standard player; weapons, shields and amulets are centred in item space.
3. Reduces faces to `--max-faces` (default 2400; `lowpoly` output already fits, so it isn't decimated).
4. Snaps vertices to the integer grid and colours to the RS palette.
5. Encodes the classic model format, then decodes it again and requires an exact match.

It writes `.dat`/`.gz`, `rs_model.obj`, `preview.png` and `sprite.png` per model, plus `report.json` and `SHEET.png`.

Example for a single model file:
```sh
python3 pipeline/stage3_models_to_rs.py --in my_sword.glb --slot weapon --up z --forward -y
```

## Refine: iterate renders, adding faces until the model matches the design
`pipeline/refine_to_match.py` is a stage-2 backend that refines in a closed loop.
Use it in place of `stage2_images_to_models.py`:

```sh
python3 pipeline/refine_to_match.py                 # all items -> pipeline_out/02_models/<code>/
python3 pipeline/refine_to_match.py --only B06 --target 0.95 --max-faces 2400
python3 pipeline/stage3_models_to_rs.py             # then convert as usual
python3 verify/runelite_check.py pipeline_out/03_rs # RuneLite decodes every model identically
```

Each round does four things:

1. **Render.** Renders the model's front view at the design's own resolution. The render is exact and pixel-aligned.
2. **Score.** Compares the render with the design. The score combines silhouette IoU and colour accuracy, i.e. the share of design pixels whose facet colour is within reach of the design's colour there.
3. **Add faces.** Places new points where the error is worst:
   - a silhouette miss snaps to the exact outline
   - a colour miss snaps onto the nearest colour border, so triangle edges follow the design's shapes
4. **Retriangulate.** Rebuilds the triangles from the new point set.

A round that makes the match worse is undone, and its spots are skipped next time. The loop stops at the first of these:

- `--target` reached
- the next round would pass the RS face budget (`--max-faces`, front + back)
- a plateau: the best score rose less than `--min-gain` over the last 3 rounds, or 6 while under half the budget

### Shadows and texture (`--mode detail`, the default)

- **Colours.** Each face takes the design's true colour under it, so the refinement also chases:
  - baked shadows and ambient occlusion
  - highlights
  - surface texture: scales, cracks, weave, glow lines

  Only half of the broad light gradient is removed (`shading_target`), because the RS client lights the model by its normals too.
- **Shadows in the geometry.** Pixels darker than their surroundings, such as gaps between plates, recesses and eye slits, become dents in the depth (`--cavity`, default 0.06). In-game lighting then shades them as well.
- **Coarse back.** The back is the front simplified with the rim locked (`collapse_interior`), so the model stays closed. It uses `--back-share` of the budget (default 15%) instead of half, which leaves about 85% of the faces for visible front detail. `--back-share 0` mirrors the front onto the back as before.
- **Capes.** Stage 3 turns capes made from the design sheet around, so the artwork side faces away from the wearer, as seen from behind in game. Other slots are unchanged. External models keep using `--forward`.
- **Textures, technically.** RS old-format models also support texture-mapped faces, but those reference texture IDs in the client's own texture cache. The colours here are baked per face, which works on any client without cache edits.

`--mode flat` gives the earlier look: 8 flat tones with the shading removed.

### Outputs per item

- `model.obj`
- `meta.json`, which holds `match`, `stop`, `mode` and the round-by-round `history`
- `refine.png`, a strip showing the design, selected rounds with face counts and scores, and the final lit 3D model

## Blender (mold the designs with real Blender modelling)
Blender runs headless as a Python module, with no GUI or GPU needed:
```sh
./scripts/setup_blender.sh                                   # one-time: Blender 5.2 (bpy) in .venv-blender
.venv-blender/bin/python pipeline/blender_mold.py --only B14  # mold -> pipeline_out/02_models/
python3 pipeline/stage3_models_to_rs.py --only B14           # -> RS
```
For each item, Blender:
1. Builds a solid from the traced outline, with a chamfered rim.
2. Remeshes it and moulds the front and back from the depth map.
3. Uses its own collapse decimation to reach the face budget (`--faces`, default 1800).
4. Projects the design's flat colours onto each face.

**Compared with `lowpoly`:** Blender gives real thickness, bevelled edges and a solid side view; weapons and tools look clearly more three-dimensional. `lowpoly` keeps more surface detail, such as emblems and stars, and stays the default. Try both on a batch with `tools/compare.py --pipeline`.

**Your own Blender scripts.** Any Blender Python script runs the same way with `.venv-blender/bin/python`; that includes scripts written by the Hermes `render-lab-3d` deck's procedural-modeler. Have the script export a `.glb`/`.obj`, then convert it with `stage3_models_to_rs.py --in <file> --slot <slot>`.

## Meshy (AI image-to-3D)
One-time setup (environment settings: cloud environment menu in the title bar → Edit):
1. Add your Meshy API key under **Network secrets** (or as an environment variable) named `MESHY_API_KEY`. Never paste it into a chat or commit it.
2. Under **Network access**, add `api.meshy.ai` to **Allowed domains**, plus the host Meshy serves model files from (`assets.meshy.ai` at the time of writing; the first run's error message names the host if it differs).
3. Start a new session.

Then:
```sh
python3 pipeline/stage2_images_to_models.py --backend meshy --dry-run            # what would be sent (free)
python3 pipeline/stage2_images_to_models.py --backend meshy --only B12 --max-tasks 2   # try two items first
python3 pipeline/stage3_models_to_rs.py --only B12                                # convert to RS
python3 pipeline/stage2_images_to_models.py --backend meshy                        # then the rest
```
- **Spend control.** Each new task costs Meshy credits. `--max-tasks N` caps new tasks per run, and `--dry-run` calls nothing.
- **Resume.** Task ids are saved to `pipeline_out/02_models/<code>/meshy_task.json` the moment they're created, so re-running resumes pending tasks and skips finished ones instead of paying again. To deliberately regenerate an item, delete its `meshy_task.json` and `source.glb`.
- **Defaults:** `--meshy-polycount 2000` (fits the RS budget without decimation), triangle topology, textured, no PBR.
- **Other options:** `--meshy-model` picks a specific Meshy model, and `--meshy-no-texture` gives geometry only.
- **Checking orientation.** Meshy GLBs are y-up, which matches stage 3's defaults. Check the first `preview.png`; if an item is facing the wrong way, re-run stage 3 with `--forward -z`.
- **Verified so far.** The client is tested against a local fake server (`tests/test_meshy.py`): submit, poll, download, retries, failures, resume and the task cap. It has **not** yet made a real Meshy call from here, because this environment can't reach `api.meshy.ai` until access is allowed. The first real run will confirm the response format. The client already accepts `{"result": id}` or `{"id": id}`, and `task_error` as null or `{message}`.

Compare against the sheet with `python3 tools/compare.py --pipeline` (writes `pipeline_out/compare/`).

## How this relates to `out/`
`out/` holds the hand-built models from `rsgen/items.py`, and those remain the higher-quality set. This pipeline is the automatic route:
- New designs: add a sheet and run it.
- Better 3D: plug in an AI image-to-3D tool's output.
- Anything else: convert any 3D model to RS.
