# Nuke-Batch-Renderer  

A standalone PyQt5 desktop tool that batch renders Write nodes from multiple Nuke scripts — without opening Nuke manually for each file.

This tool parses `.nk` files, extracts Write nodes, lets you choose the render order, and executes renders directly through the Nuke executable.

---

## Features  

### Parse Nuke Scripts  
- Reads `.nk` files directly  
- Detects all Write nodes  
- Extracts:
  - Node name  
  - Output file path  
  - Source script  

No need to open scripts inside Nuke to check Write nodes.

---

### Batch Render Multiple Scripts  
- Add multiple `.nk` files  
- Import all Write nodes at once  
- Select which nodes to render  
- Render using Nuke’s command-line (`-X` flag)  

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
3. Add `.nk` script files  
4. Click **Import Write Nodes**  
5. Select nodes you want to render  
6. Adjust render order if needed  
7. Click **Render**  

The tool will execute renders using:

```
nuke -X WriteNodeName script.nk
```

---

## Installation  

1. Ensure Python 3 is installed  
2. Install required dependency:

```
pip install PyQt5
```

3. Run the script:

```
python batch_renderer.py
```

---

## Prerequisites  

- Nuke (installed on your system)  
- Python 3  
- PyQt5  

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