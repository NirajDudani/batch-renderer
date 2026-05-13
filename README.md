# Nuke-Batch-Renderer  

![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![Nuke](https://img.shields.io/badge/Nuke-any%20recent%20release-yellow)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15%2B-41cd52)
![License](https://img.shields.io/badge/License-MIT-green)

A standalone PyQt5 desktop tool that batch renders Write nodes from multiple Nuke scripts — without opening Nuke manually for each file.

This tool parses `.nk` and `.nknc` files, extracts Write nodes, lets you choose the render order, and executes renders directly through the Nuke executable.

---

## Features  

### Parse Nuke Scripts  
- Reads `.nk` and `.nknc` (Non-Commercial) files  
- Detects all Write nodes  
- Extracts:
  - Node name  
  - Output file path  
  - Source script  

No need to open scripts inside Nuke to check Write nodes.

---

### Batch Render Multiple Scripts  
- Add multiple `.nk` / `.nknc` files  
- Import all Write nodes at once  
- Select which nodes to render  
- Render using Nuke's command-line (`-X` flag)  

---

### Non-Commercial Mode  
- Enable the **Non-Commercial Mode** checkbox to pass `--nc` to Nuke  
- When importing `.nknc` files, the tool automatically prompts to enable this mode  

---

### Custom Render Order  
- Reorder Write nodes using:
  - Move Up  
  - Move Down  
- Render executes in selected order  

---

### Nuke Executable Detection  
- Browse and select your Nuke installation  
- Supports:
  - Windows  
  - macOS  
  - Linux  

---

### Render Progress & Error Handling  
- Progress dialog during rendering  
- Cancel option  
- Displays detailed error messages if rendering fails  

---

## Workflow  

1. Launch the tool  
2. Select your Nuke executable location  
3. Add `.nk` or `.nknc` script files  
4. Click **Import Write Nodes**  
5. Select nodes you want to render  
6. Adjust render order if needed  
7. Click **Render**  

The tool executes renders using:

```
nuke -i -X WriteNodeName script.nk
```

With Non-Commercial Mode enabled:

```
nuke --nc -i -X WriteNodeName script.nknc
```

---

## Prerequisites  

- [Python 3.7+](https://www.python.org/downloads/)  
- [PyQt5](https://pypi.org/project/PyQt5/)  
- Nuke (installed on your system)  

---

## Installation  

### 1. Download the tool

**Option A — Clone with Git:**
```
git clone https://github.com/your-username/batch-renderer.git
cd batch-renderer
```

**Option B — Download ZIP:**  
Click **Code → Download ZIP** on the GitHub page, then extract the folder.

---

### 2. Install Python

If you don't have Python installed:

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download and run the installer for your OS
3. **Windows:** check "Add Python to PATH" during installation
4. Verify the installation by opening a terminal and running:

```
python --version
```

---

### 3. Install PyQt5

Open a terminal (or Command Prompt on Windows) inside the project folder and run:

```
pip install PyQt5
```

If `pip` is not found, try:

```
python -m pip install PyQt5
```

---

### 4. Run the tool

```
python batchRenderer.py
```

On some systems you may need to use `python3` instead:

```
python3 batchRenderer.py
```

---

## Use Case  

This tool is useful for:
- Overnight batch renders  
- Rendering multiple shots at once  
- Re-rendering multiple Write nodes quickly  
- Pipeline automation experiments  
- Artists with no access to render-farms  

---

## Contribution  

Contributions are welcome! Feel free to submit pull requests or raise issues for any suggestions or bugs.
