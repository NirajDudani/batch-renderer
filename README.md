# Channel Sorter for Nuke

A Python GUI tool for [Foundry Nuke](https://www.foundry.com/products/nuke) that scans a Read node's AOVs, sorts them into Material / Light / Utility / ID groups, and auto-builds a clean Shuffle2 + Merge2 tree — with optional labeled backdrops — so multi-pass compositing setups are built in seconds instead of minutes.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Nuke](https://img.shields.io/badge/Nuke-11%2B-yellow)
![PySide2](https://img.shields.io/badge/PySide2-bundled%20with%20Nuke-41cd52)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What It Does

Select a Read node with a multi-channel EXR (or any node carrying AOVs), run **Sort Channels**, and the tool lists every unique layer in a checkbox dialog. Pick the AOVs you want, choose whether to add backdrops, and hit OK — Channel Sorter drops an Unpremult, spawns a named Shuffle2 for each selected channel, categorizes them (diffuse/spec/normal → *Material AOVs*, lightgroups/RGBA → *Light Groups*, cryptomatte/motion vectors → *Utilities*, anything with "id" → *IDs*), auto-iterates node names so nothing collides with an existing build, merges same-base AOVs with a plus-operation Merge2, and optionally wraps each category in a labeled backdrop.

---

## Installation

### Step 1 — Download

Clone the repo or download the ZIP:

```bash
git clone https://github.com/YOUR_USERNAME/channel-sorter.git
```

Or click **Code → Download ZIP** on the GitHub page and extract it.

### Step 2 — Copy the Script

Copy `channel-sorter.py` into your `.nuke` directory. The `.nuke` folder lives in your home directory by default:

| OS | Default Path |
|----|-------------|
| Windows | `C:\Users\<you>\.nuke\` |
| macOS | `/Users/<you>/.nuke/` |
| Linux | `/home/<you>/.nuke/` |

> **Tip:** If you don't see a `.nuke` folder, open Nuke once and it will create one automatically. On Windows and macOS, hidden folders may not show by default — enable "Show hidden files" in your file browser.

### Step 3 — Rename the File

**Important:** Rename `channel-sorter.py` to `channel_sorter.py` (hyphen → underscore). Python cannot import modules whose filenames contain hyphens, so `import channel-sorter` will fail.

### Step 4 — Register the Script

Open (or create) the file `menu.py` inside your `.nuke` directory and add this single line:

```python
import channel_sorter
```

### Step 5 — Restart Nuke

Close and reopen Nuke. You should now see a new menu entry at **Nuke → Tools → Sort Channels**.

---

## How to Use It

### 1. Select a Source Node

In the Node Graph, select a Read node — or any node whose output carries AOVs (a Shuffle, a Merge, a Group output, etc.). The tool reads channels from whichever node is currently selected.

### 2. Launch the Tool

Go to **Nuke → Tools → Sort Channels**. A dialog appears listing every unique AOV layer found on the selected node:

```
┌────────────────────────────────┐
│  Select the Channels:          │
│   [x] rgba                     │
│   [x] diffuse_direct           │
│   [x] diffuse_indirect         │
│   [x] specular_direct          │
│   [ ] cryptomatte00            │
│   [ ] motion_vectors           │
│                                │
│  Add Backdrop?   [ No  ▼ ]     │
│                                │
│              [ OK ]            │
└────────────────────────────────┘
```

### 3. Pick Channels and Backdrop Option

Tick the layers you want to shuffle out. Use the **Add Backdrop?** dropdown to decide whether to wrap each category in a labeled backdrop (*No* by default). Click **OK**.

### 4. Review the Auto-Generated Tree

Channel Sorter builds this structure downstream of the selected node:

| Node | Purpose |
|------|---------|
| `Unpremult` | Unpremultiplies the source before shuffling, so math on individual AOVs is correct |
| `Shuffle2` (one per channel) | Named `<channel>_<iteration>` (e.g. `diffuse_direct_1`) — pulls that single layer |
| `Merge2` (plus) | Auto-created when two channels share a base name (e.g. `diffuse_direct` + `diffuse_indirect`) to sum them back together |
| Backdrops *(optional)* | Four labeled backdrops — *Material AOVs*, *Light Groups*, *Utilities*, *ID* — each wrapping its own Shuffle/Merge nodes |

The iteration suffix means you can run the tool multiple times on the same script without name collisions — `diffuse_direct_1`, `diffuse_direct_2`, etc.

---

## How Channels Are Categorized

The tool uses keyword matching on the lower-cased channel name:

| Category | Matches channels containing… |
|----------|------------------------------|
| Light Groups | `light`, `rgba` |
| IDs | `id` |
| Material AOVs | `diffuse`, `specular`, `reflection`, `refraction`, `normal`, `glossiness`, `roughness`, `metallic`, `ambient occlusion`, `emission`, `depth`, `shadow`, `transmission`, `displacement`, `subsurface scattering`, `clearcoat`, `sheen`, `fresnel`, `anisotropy`, `velocity` |
| Utilities | `motion vectors`, `z-depth`, `cryptomatte`, `object id`, `material id`, `layer masks`, `ambient light`, `wireframe`, `caustics`, `light masking` |

Matching priority is top-down — a channel that contains both `light` and `diffuse` (e.g. `light_diffuse`) falls into **Light Groups**. Channels that don't match any keyword are silently skipped (not added to the tree). If your renderer uses non-standard AOV names, see [Customizing the Keywords](#customizing-the-keywords) below.

---

## Customizing the Keywords

The keyword lists live at the top of the `sort_nodes()` function in `channel_sorter.py`:

```python
material_aov_keywords = [
    "diffuse", "specular", "reflection", ...
]

utilities = [
    "motion vectors", "z-depth", "cryptomatte", ...
]
```

Edit these lists to match your studio's naming conventions (Arnold `RGBA_*`, V-Ray `VRay*`, Redshift `*_Direct`, etc.), save the file, and restart Nuke.

---

## Requirements

- **Nuke 11+** (any version with PySide2 bundled — this includes most modern releases)
- No external Python packages required; everything used (`nuke`, `nukescripts`, `PySide2`) ships with Nuke's embedded Python.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Menu entry doesn't appear | Make sure the file is named `channel_sorter.py` (underscore, not hyphen) and lives directly inside `.nuke/`. Check Nuke's Script Editor for import errors. |
| `ModuleNotFoundError: No module named 'channel_sorter'` | The filename probably still has a hyphen. Rename it to `channel_sorter.py`. |
| `SyntaxError: invalid syntax` on the `import channel-sorter` line | Same issue — Python can't import hyphenated names. Rename the file and the import line to use an underscore. |
| The tool runs automatically when Nuke starts | The script calls `sort_channels()` at module load. Remove or comment out the standalone `sort_channels()` call near the bottom of the file — only the `nuke.menu(...).addCommand(...)` line should remain at module level. |
| "No node selected" / the tool errors out | Select a node in the Node Graph before launching. The tool reads channels from `nuke.selectedNode()` and needs exactly one selection. |
| Some AOVs don't end up in any backdrop | Only channels whose names match a keyword in the four categories are sorted. Unmatched channels are skipped. Add your naming pattern to `material_aov_keywords` or `utilities`. |
| Shuffle nodes pile up on top of each other | The tool offsets each new Shuffle by 110 px along X from the source node's position. If your source node is inside a cramped area of the graph, move it to open space and re-run. |

---

## Known Limitations

- **Keyword-based matching.** If a channel name doesn't contain one of the listed keywords, it's silently dropped — no warning. Check the Script Editor if a channel you expected is missing from the build.
- **Runs on import.** The script calls `sort_channels()` at the bottom of the file, which triggers the dialog the moment Nuke imports it. This should be removed so the tool only runs when clicked from the menu (see Troubleshooting).
- **No undo grouping.** Each created node is its own undo step — rolling back a full build takes multiple Ctrl+Z presses.
- **No preview.** You commit to the build when you click OK; there's no dry-run mode showing what will be created.

---

## Roadmap

- [ ] Remove the module-level `sort_channels()` call so the tool only fires from the menu
- [ ] Wrap the whole build in a single `nuke.Undo()` block so one Ctrl+Z reverts everything
- [ ] Configurable keyword lists via a JSON config file (no code edits required)
- [ ] "Select all / None" buttons in the checkbox dialog
- [ ] Per-category backdrop color presets
- [ ] Dry-run preview showing which nodes *would* be created

---

## Contributing

Contributions are welcome — feel free to open issues or submit pull requests. If you're adding a feature, please test it against a multi-channel EXR with a mix of Material, Light, Utility, and ID AOVs, and against a channel whose name doesn't match any keyword (to confirm the skip-path is graceful).

---

## License

MIT — use it however you like.
