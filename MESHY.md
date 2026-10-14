# Meshy: real 3D models from the designs

`meshy_input/` has a clean upload image for every item: 1024×1024, transparent
background, cut from `reference_sheet.jpg`. `meshy_input/contact_sheet.png` shows all of them.
Regenerate them with `python tools/meshy_inputs.py`; the optional `pip install opencv-python-headless`
repairs dark armour cutouts with GrabCut.

There are two ways to use Meshy.

## A. By hand on meshy.ai (no setup)

1. Open meshy.ai → **Image to 3D** and upload `meshy_input/<code>_<name>.png`.
2. Settings:
   - texture: on
   - topology: triangle
   - polycount: the lowest it offers (around 3–5k)
   - symmetry: on for armour and helms, auto for weapons
3. Download as **GLB** and name it `<code>.glb`, e.g. `B08_3.glb`.
4. Give the GLBs to Claude. Put them in a `meshy_models/` folder in the repo and push, or attach them to the chat.

## B. Let Claude call Meshy from your PC (automated)

Claude runs the pipeline on your PC, and your key never goes into the chat.

1. **Get an API key.** Go to meshy.ai → your account → **API**. API calls use paid credits, so check that your plan
   includes them.
2. **Store it on your PC.** Open PowerShell and run this once, with your key in place of the placeholder:
   ```powershell
   setx MESHY_API_KEY "msy_your_key_here"
   ```
   Then close PowerShell and open a new window; `setx` only applies to new windows.
3. **Get the project and its tools** (needs Git and Python 3.10+):
   ```powershell
   cd C:\Users\baseb\rsps
   git clone https://github.com/iamchrisvelez-bit/RSPS---reimagined.git
   cd RSPS---reimagined
   git checkout rsps-redesigns
   pip install -r requirements.txt opencv-python-headless
   ```
4. **Start Claude Code in that folder**, using either of these:
   - the **Claude desktop app**: open a Code session and choose this folder, or
   - in the same PowerShell window, `claude` for a terminal session. Use `claude remote-control` instead if you
     want to drive it from the Claude app on your phone or browser.
5. **Ask Claude** something like *"Run Meshy on B08_3, B12_2 and B05_4 and show me the QA sheets."*
   The commands it uses are below. Always do a dry run first: it shows what would be sent and costs nothing.
   ```powershell
   python pipeline/stage2_images_to_models.py --backend meshy --only B08_3 --dry-run
   python pipeline/stage2_images_to_models.py --backend meshy --only B08_3 --max-tasks 1
   ```
   - `--max-tasks` caps how many paid tasks one run may start.
   - Task ids are saved as soon as each task is submitted (`pipeline_out/02_models/<code>/meshy_task.json`), so an
     interrupted run resumes instead of paying twice.

### Or from a Claude cloud session

Two settings are needed in the cloud environment's settings: the session title bar's environment menu, then **Edit**.

- **Key:** add `MESHY_API_KEY` under Network secrets, or as an environment variable.
- **Network:** add `api.meshy.ai` and `assets.meshy.ai` under **Network access → Allowed domains**. The second is
  the download host; if a download is refused, the error names the host to add.

Start a new session afterwards so it picks these up.

## What happens next

Claude reduces each Meshy model to an OSRS-style face count with flat colours, then puts it through the same
fitting, animation, swap and QA steps as the current models (SWAP.md, `tools/qa_render.py`). It compares the
results side by side with the current versions before anything replaces them.
