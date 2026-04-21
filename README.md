# Batch Renderer for Nuke

A standalone Python GUI tool that batch-renders Write nodes from multiple [Foundry Nuke](https://www.foundry.com/products/nuke) scripts — so compositors can queue overnight renders across many `.nk` files without opening Nuke's GUI for each one.

![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![Nuke](https://img.shields.io/badge/Nuke-any%20recent%20release-yellow)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15%2B-41cd52)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What It Does

Launch the tool, point it at your Nuke executable, and drop in as many `.nk` scripts as you want. Batch Renderer parses the scripts as plain text, pulls every Write node into a live table, and lets you tick which ones to render, reorder the queue, and kick off all the renders through Nuke's command-line (`-X`) — with a progress dialog and cancel button. Runs entirely outside Nuke, so you don't tie up a GUI license while rendering.

---

## Installation

### Step 1 — Download

Clone the repo or download the ZIP:

```bash
git clone https://github.com/YOUR_USERNAME/batch-renderer.git
```

Or click **Code → Download ZIP** on the GitHub page and extract it.

### Step 2 — Install Python and PyQt5

Unlike a Nuke plugin, Batch Renderer runs on your **system Python**, not Nuke's embedded one. You'll need Python 3.7+ and PyQt5.

A virtual environment is strongly recommended so the tool's dependencies stay isolated from your system Python.

**Windows (PowerShell):**

```powershell
cd batch-renderer
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install PyQt5
```

**macOS / Linux:**

```bash
cd batch-renderer
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install PyQt5
```

> **Tip:** On some Debian/Ubuntu systems you may also need `sudo apt install libxcb-xinerama0` for Qt to find its platform plugin.

### Step 3 — Run the Tool

From inside the project folder (with the virtual environment activated):

```bash
python batchRenderer.py
```

The main window should appear.

### Step 4 — Point It at Your Nuke Executable

First time you launch, click **Browse...** next to **Nuke Location** and select the Nuke executable itself — not the install folder or the `.app` bundle:

| OS | Example Path |
|----|--------------|
| Windows | `C:\Program Files\Nuke15.0v4\Nuke15.0.exe` |
| macOS | `/Applications/Nuke15.0v4/Nuke15.0v4.app/Contents/MacOS/Nuke15.0` |
| Linux | `/usr/local/Nuke15.0v4/Nuke15.0` |

> **Note:** On macOS the executable is *inside* the `.app` bundle. Right-click the `.app` → *Show Package Contents* → `Contents/MacOS/` if Finder won't let you pick it directly.

---

## How to Use It

### 1. Add Nuke Scripts

In the **Nuke Script Files** panel, click **Add Files** and select one or more `.nk` scripts. Use **Remove File** to drop anything you added by mistake.

### 2. Import Write Nodes

Click **Import Write Nodes**. The tool parses every script as plain text and populates the table with every top-level Write node it finds:

| Column | Meaning |
|--------|---------|
| Render | Checkbox — tick to include this node in the render queue |
| Name | Write node name (e.g. `Write1`, `Write_mp4`) |
| Path | Output file path defined on the Write node |
| Script File | The `.nk` script this node belongs to |

All nodes are checked by default. Writes nested inside Groups or LiveGroups won't appear — pull them to the top level of the script if you need them rendered here.

### 3. Select and Reorder

Uncheck any Write nodes you don't want to render this pass. Select a row and use **Move Up** / **Move Down** to set the order — renders execute top-to-bottom in the order shown.

### 4. Render

Click **Render**. A progress dialog tracks each node as it goes:

```
Rendering Write1 from shot_010_comp.nk...   [2 / 7]
```

Hit **Cancel** at any time to stop the queue after the current node finishes. When the batch completes, you'll get either a success message or a summary dialog listing any failures with their stderr output.

Under the hood each render is dispatched as:

```
<nuke-executable> -X <WriteNodeName> <script.nk>
```

Each render runs to completion before the next one starts, using the frame range already set on the Write node.

---

## Supported Input

| Item | What's supported |
|------|------------------|
| Nuke scripts | Standard ASCII `.nk` files (Nuke's default serialization format) |
| Write nodes | Any top-level `Write { ... }` block in the script |
| Output formats | Whatever the Write node itself is configured for — the tool doesn't override format, codec, or frame range |

---

## Requirements

- **Python 3.7+** (system install or virtualenv)
- **PyQt5** (installed via `pip`)
- **Nuke** — any recent commercial or non-commercial release, installed and licensed separately. This tool does **not** bundle Nuke.
- **OS:** Windows, macOS, or Linux.

> **Licensing note:** Command-line rendering requires a license that allows it. Commercial and Non-Commercial Nuke both support `-X`; some older Personal Learning Edition builds do not. Verify with a manual `nuke -X WriteNode script.nk` in a terminal if unsure.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Please select a valid Nuke Location!" | You haven't set the Nuke path, or the path no longer exists. Re-browse to the executable (not the folder or `.app`). |
| No Write nodes appear after clicking **Import Write Nodes** | Open the `.nk` file in a text editor and check for `Write {` blocks. The parser only handles Nuke's default ASCII format — encrypted or Gizmo-wrapped scripts won't parse. Writes inside Groups are also skipped; flatten or pull them to the top level. |
| Render fails with a licensing error | Confirm `-X` command-line rendering is allowed on your license. Run `nuke -X WriteName script.nk` manually from a terminal to isolate whether the issue is this tool or Nuke itself. |
| UI appears frozen during a long render | Renders run sequentially on the main thread, so the window only repaints between nodes. The queue will still complete; Cancel takes effect after the current render finishes. |
| `ModuleNotFoundError: No module named 'PyQt5'` | The virtual environment isn't activated, or PyQt5 wasn't installed into it. Re-activate the venv and run `pip install PyQt5`. |

---

## Contributing

Contributions are welcome — feel free to open issues or submit pull requests. If you're adding a feature, please test it against a mix of scripts: single Writes, multiple Writes per script, and a deliberately broken path to confirm the error-handling path still surfaces failures cleanly.

---

## License

MIT — use it however you like.
