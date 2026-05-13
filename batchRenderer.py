import os
import sys
import subprocess
import tempfile
from PyQt5 import QtWidgets, QtCore, QtGui


def get_nuke_env(nuke_exe_path=None):
    """Get environment with Nuke license settings preserved."""
    env = os.environ.copy()
    
    # Get the actual user profile path
    user_profile = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    local_appdata = os.environ.get('LOCALAPPDATA', os.path.join(user_profile, 'AppData', 'Local'))
    
    # Preserve Foundry login token path - use explicit path
    foundry_token_path = os.path.join(local_appdata, 'Foundry', 'Tokens')
    if os.path.exists(foundry_token_path):
        env['FOUNDRY_LOGIN_TOKEN_PATH'] = foundry_token_path
    
    # Set user profile variables explicitly
    env['USERPROFILE'] = user_profile
    env['HOMEDRIVE'] = os.environ.get('HOMEDRIVE', os.path.splitdrive(user_profile)[0])
    env['HOMEPATH'] = os.environ.get('HOMEPATH', os.path.splitdrive(user_profile)[1])
    env['LOCALAPPDATA'] = local_appdata
    env['APPDATA'] = os.environ.get('APPDATA', os.path.join(user_profile, 'AppData', 'Roaming'))
    
    # Add Nuke's directory to PATH so it can find its own DLLs
    if nuke_exe_path:
        nuke_dir = os.path.dirname(nuke_exe_path)
        if nuke_dir not in env.get('PATH', ''):
            env['PATH'] = nuke_dir + ';' + env.get('PATH', '')
    
    # Ensure RLM license paths are set
    rlm_paths = [
        r'C:\ProgramData\The Foundry\RLM',
        r'C:\Program Files\The Foundry\RLM',
        r'C:\Program Files (x86)\The Foundry\RLM',
    ]
    existing_rlm = env.get('RLM_LICENSE', '')
    new_rlm_paths = [p for p in rlm_paths if os.path.exists(p)]
    if existing_rlm:
        new_rlm_paths.insert(0, existing_rlm)
    if new_rlm_paths:
        env['RLM_LICENSE'] = ';'.join(new_rlm_paths)
    
    # Also set foundry_LICENSE for older Nuke versions
    env['foundry_LICENSE'] = env.get('RLM_LICENSE', '')
    
    # Copy login license info if present
    for key in ['NUKE_LICENSE', 'NUKE_TRIAL', 'FOUNDRY_LICENSE', 'foundry_LICENSE']:
        if key in os.environ:
            env[key] = os.environ[key]
    
    return env


def get_effective_path(node):
    if node.get('override_dir'):
        return os.path.join(node['override_dir'], os.path.basename(node['file'])).replace('\\', '/')
    return node['file']


def validate_override_dirs(nodes):
    errors = []
    for node in nodes:
        if node.get('override_dir') and not os.path.isdir(node['override_dir']):
            errors.append(
                f"Override directory does not exist for '{node['name']}': {node['override_dir']}"
            )
    return errors


class NukeScriptParser:
    def __init__(self):
        self.write_nodes = []

    def parse_nuke_file(self, file_path):
        self.write_nodes = []
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            nodes = content.split("Write {")
            if len(nodes) > 1:
                for i in range(1, len(nodes)):
                    node_text = nodes[i]
                    end_idx = node_text.find("\n}")
                    if end_idx != -1:
                        node_text = node_text[:end_idx]
                    name = "Write"
                    name_match = self._extract_attribute(node_text, "name")
                    if name_match:
                        name = name_match
                    file_path = ""
                    file_match = self._extract_attribute(node_text, "file")
                    if file_match:
                        file_path = file_match
                    self.write_nodes.append({
                        'name': name,
                        'file': file_path,
                        'script': file_path,
                        'node_text': node_text
                    })
            return self.write_nodes
        except Exception as e:
            print(f"Error parsing Nuke file: {str(e)}")
            return []

    def _extract_attribute(self, text, attr_name):
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(f"{attr_name} "):
                parts = line.split(" ", 1)
                if len(parts) > 1:
                    value = parts[1]
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    return value
        return None

    def modify_write_node_file_path(self, content, node_name, new_file_path):
        blocks = content.split("Write {")
        if len(blocks) <= 1:
            return content
        result = [blocks[0]]
        for block in blocks[1:]:
            end_idx = block.find("\n}")
            if end_idx == -1:
                result.append(block)
                continue
            node_body = block[:end_idx]
            remainder = block[end_idx:]
            lines = node_body.split("\n")
            is_target = any(line.strip() == f"name {node_name}" for line in lines)
            if is_target:
                new_lines = []
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("file ") and not stripped.startswith("file_"):
                        indent = " " * (len(line) - len(line.lstrip()))
                        new_lines.append(f"{indent}file {new_file_path}")
                    else:
                        new_lines.append(line)
                node_body = "\n".join(new_lines)
            result.append(node_body + remainder)
        return "Write {".join(result)


class BatchRenderTool(QtWidgets.QMainWindow):
    def __init__(self):
        super(BatchRenderTool, self).__init__()
        self.setWindowTitle("Nuke Batch Renderer")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.nuke_files = []
        self.node_models = []
        self.parser = NukeScriptParser()
        self.nuke_path = ""
        self.non_commercial_mode = False
        self.setup_ui()

    def setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

        nuke_path_layout = QtWidgets.QHBoxLayout()
        nuke_path_label = QtWidgets.QLabel("Nuke Location:")
        self.nuke_path_edit = QtWidgets.QLineEdit()
        self.nuke_path_btn = QtWidgets.QPushButton("Browse...")
        self.nuke_path_btn.clicked.connect(self.browse_nuke_executable)
        nuke_path_layout.addWidget(nuke_path_label)
        nuke_path_layout.addWidget(self.nuke_path_edit)
        nuke_path_layout.addWidget(self.nuke_path_btn)
        main_layout.addLayout(nuke_path_layout)

        # Non-commercial mode checkbox
        nc_layout = QtWidgets.QHBoxLayout()
        self.nc_checkbox = QtWidgets.QCheckBox("Non-Commercial Mode (--nc)")
        self.nc_checkbox.stateChanged.connect(self.toggle_non_commercial)
        nc_layout.addWidget(self.nc_checkbox)
        nc_layout.addStretch()
        main_layout.addLayout(nc_layout)

        files_group = QtWidgets.QGroupBox("Nuke Script Files")
        files_layout = QtWidgets.QVBoxLayout()
        files_group.setLayout(files_layout)
        self.files_list = QtWidgets.QListWidget()
        files_layout.addWidget(self.files_list)
        file_btns = QtWidgets.QHBoxLayout()
        self.add_file_btn = QtWidgets.QPushButton("Add Files")
        self.add_file_btn.clicked.connect(self.add_nuke_files)
        self.remove_file_btn = QtWidgets.QPushButton("Remove File")
        self.remove_file_btn.clicked.connect(self.remove_nuke_file)
        self.import_writes_btn = QtWidgets.QPushButton("Import Write Nodes")
        self.import_writes_btn.clicked.connect(self.import_write_nodes)
        file_btns.addWidget(self.add_file_btn)
        file_btns.addWidget(self.remove_file_btn)
        file_btns.addWidget(self.import_writes_btn)
        files_layout.addLayout(file_btns)
        main_layout.addWidget(files_group)

        nodes_group = QtWidgets.QGroupBox("Write Nodes")
        nodes_layout = QtWidgets.QVBoxLayout()
        nodes_group.setLayout(nodes_layout)
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Render", "Name", "Effective Path", "Output Dir", "Script File"])
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        nodes_layout.addWidget(self.table)
        btn_layout = QtWidgets.QHBoxLayout()
        self.up_btn = QtWidgets.QPushButton("Move Up")
        self.up_btn.clicked.connect(self.move_up)
        self.down_btn = QtWidgets.QPushButton("Move Down")
        self.down_btn.clicked.connect(self.move_down)
        btn_layout.addWidget(self.up_btn)
        btn_layout.addWidget(self.down_btn)
        nodes_layout.addLayout(btn_layout)
        main_layout.addWidget(nodes_group)

        action_btns = QtWidgets.QHBoxLayout()
        self.render_btn = QtWidgets.QPushButton("Render")
        self.render_btn.clicked.connect(self.do_render)
        self.cancel_btn = QtWidgets.QPushButton("Exit")
        self.cancel_btn.clicked.connect(self.close)
        action_btns.addWidget(self.render_btn)
        action_btns.addWidget(self.cancel_btn)
        main_layout.addLayout(action_btns)

    def browse_nuke_executable(self):
        default_paths = {
            "win32": "C:\\Program Files\\Nuke*",
            "darwin": "/Applications/Nuke*.app/Contents/MacOS",
            "linux": "/usr/local/Nuke*"
        }
        initial_dir = os.path.expanduser("~")
        if sys.platform in default_paths:
            import glob
            paths = glob.glob(default_paths[sys.platform])
            if paths:
                initial_dir = paths[0]
        file_filter = "Nuke Location (Nuke*.exe);;All Files (*.*)" if sys.platform == "win32" else "All Files (*.*)"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Nuke Location", initial_dir, file_filter)
        if path:
            self.nuke_path = path
            self.nuke_path_edit.setText(path)

    def add_nuke_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Nuke Script Files", "", "Nuke Files (*.nk *.nknc);;Nuke Scripts (*.nk);;Nuke Non-Commercial (*.nknc);;All Files (*.*)")
        if files:
            for file_path in files:
                if file_path not in self.nuke_files:
                    self.nuke_files.append(file_path)
                    self.files_list.addItem(os.path.basename(file_path))

    def remove_nuke_file(self):
        selected = self.files_list.currentRow()
        if selected >= 0:
            file_path = self.nuke_files.pop(selected)
            self.files_list.takeItem(selected)
            self.node_models = [m for m in self.node_models if m['script'] != file_path]
            self.update_table()

    def import_write_nodes(self):
        if not self.nuke_files:
            QtWidgets.QMessageBox.warning(self, "Error", "No Nuke files selected!")
            return
        
        # Check if any files are .nknc (non-commercial) and warn/auto-enable
        nc_files = [f for f in self.nuke_files if f.lower().endswith('.nknc')]
        if nc_files and not self.non_commercial_mode:
            reply = QtWidgets.QMessageBox.question(
                self, "Non-Commercial Script Detected",
                f"Detected {len(nc_files)} Non-Commercial script(s) (.nknc).\n\n"
                "Non-Commercial scripts require the '--nc' flag to render.\n\n"
                "Do you want to enable Non-Commercial Mode?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self.nc_checkbox.setChecked(True)
                self.non_commercial_mode = True
            else:
                QtWidgets.QMessageBox.warning(
                    self, "Warning",
                    "Non-Commercial scripts may fail to render without '--nc' flag.\n"
                    "You can enable Non-Commercial Mode manually using the checkbox."
                )
        
        self.node_models = []
        order = 1
        for script_file in self.nuke_files:
            nodes = self.parser.parse_nuke_file(script_file)
            for node in nodes:
                chk = QtWidgets.QCheckBox()
                chk.setChecked(True)
                self.node_models.append({
                    'name': node['name'],
                    'file': node['file'],
                    'script': script_file,
                    'order': order,
                    'chk': chk,
                    'override_dir': None
                })
                order += 1
        self.update_table()

    def update_table(self):
        self.table.setRowCount(len(self.node_models))
        for i, m in enumerate(self.node_models):
            chk_widget = QtWidgets.QWidget()
            chk_layout = QtWidgets.QHBoxLayout(chk_widget)
            chk_layout.addWidget(m['chk'])
            chk_layout.setAlignment(QtCore.Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)

            name_item = QtWidgets.QTableWidgetItem(m['name'])

            effective_item = QtWidgets.QTableWidgetItem(get_effective_path(m))
            effective_item.setFlags(effective_item.flags() & ~QtCore.Qt.ItemIsEditable)
            if m['override_dir']:
                effective_item.setForeground(QtGui.QBrush(QtGui.QColor('orange')))

            btn_label = '...'
            if m['override_dir']:
                btn_label = m['override_dir'] if len(m['override_dir']) <= 20 else '...' + m['override_dir'][-17:]
            btn = QtWidgets.QPushButton(btn_label)
            btn.clicked.connect(lambda checked, row=i: self._browse_override_dir(row))
            btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, row=i: self._clear_override_dir(row))
            btn_widget = QtWidgets.QWidget()
            btn_layout = QtWidgets.QHBoxLayout(btn_widget)
            btn_layout.addWidget(btn)
            btn_layout.setContentsMargins(2, 2, 2, 2)

            script_item = QtWidgets.QTableWidgetItem(os.path.basename(m['script']))
            script_item.setFlags(script_item.flags() & ~QtCore.Qt.ItemIsEditable)

            self.table.setCellWidget(i, 0, chk_widget)
            self.table.setItem(i, 1, name_item)
            self.table.setItem(i, 2, effective_item)
            self.table.setCellWidget(i, 3, btn_widget)
            self.table.setItem(i, 4, script_item)

    def _browse_override_dir(self, row):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Output Directory", "")
        if directory:
            self.node_models[row]['override_dir'] = directory
            self.update_table()

    def _clear_override_dir(self, row):
        self.node_models[row]['override_dir'] = None
        self.update_table()

    def toggle_non_commercial(self, state):
        self.non_commercial_mode = (state == QtCore.Qt.Checked)

    def _build_render_cmd(self, node, script_path):
        """Build the render command with appropriate flags."""
        cmd = [self.nuke_path]
        
        # Add non-commercial flag if enabled
        if self.non_commercial_mode:
            cmd.append('--nc')
        
        # Add interactive license flag and execute flags
        cmd.extend(['-i', '-X', node['name'], script_path])
        
        return cmd

    def _render_with_override(self, node):
        new_path = get_effective_path(node)
        with open(node['script'], 'r') as f:
            content = f.read()
        modified = self.parser.modify_write_node_file_path(content, node['name'], new_path)
        script_dir = os.path.dirname(os.path.abspath(node['script']))
        tmp_path = None
        try:
            # Use .nknc extension if the original script is non-commercial
            suffix = '.nknc' if node['script'].lower().endswith('.nknc') else '.nk'
            with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, dir=script_dir, delete=False) as tmp_file:
                tmp_file.write(modified)
                tmp_path = tmp_file.name
            cmd = self._build_render_cmd(node, tmp_path)
            env = get_nuke_env(self.nuke_path)
            nuke_dir = os.path.dirname(self.nuke_path)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                  universal_newlines=True, env=env, cwd=nuke_dir)
            stdout, stderr = proc.communicate()
            return proc.returncode, (stdout + stderr).strip()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def move_up(self):
        sel = self.table.selectedIndexes()
        if not sel:
            return
        row = sel[0].row()
        if row <= 0:
            return
        self.node_models[row], self.node_models[row-1] = self.node_models[row-1], self.node_models[row]
        self.node_models[row-1]['order'] = row
        self.node_models[row]['order'] = row + 1
        self.update_table()
        self.table.selectRow(row - 1)

    def move_down(self):
        sel = self.table.selectedIndexes()
        if not sel:
            return
        row = sel[0].row()
        if row >= len(self.node_models) - 1:
            return
        self.node_models[row], self.node_models[row+1] = self.node_models[row+1], self.node_models[row]
        self.node_models[row]['order'] = row + 1
        self.node_models[row+1]['order'] = row + 2
        self.update_table()
        self.table.selectRow(row + 1)

    def get_nodes_to_render(self):
        return [m for m in sorted(self.node_models, key=lambda x: x['order']) if m['chk'].isChecked()]

    def do_render(self):
        if not self.nuke_path or not os.path.exists(self.nuke_path):
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a valid Nuke Location!")
            return
        nodes = self.get_nodes_to_render()
        if not nodes:
            QtWidgets.QMessageBox.warning(self, "Error", "Select at least one node!")
            return
        dir_errors = validate_override_dirs(nodes)
        if dir_errors:
            QtWidgets.QMessageBox.warning(
                self, "Invalid Override Directories",
                "The following nodes have invalid output directories and will be skipped:\n\n"
                + "\n".join(dir_errors)
            )
            nodes = [n for n in nodes if not (n.get('override_dir') and not os.path.isdir(n['override_dir']))]
            if not nodes:
                return
        progress = QtWidgets.QProgressDialog("Rendering nodes...", "Cancel", 0, len(nodes), self)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setWindowTitle("Rendering")
        progress.show()
        errors = []
        for i, node in enumerate(nodes):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            progress.setLabelText(f"Rendering {node['name']} from {os.path.basename(node['script'])}...")
            try:
                output_dir = os.path.dirname(get_effective_path(node))
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                if node.get('override_dir'):
                    returncode, output = self._render_with_override(node)
                else:
                    cmd = self._build_render_cmd(node, node['script'])
                    env = get_nuke_env(self.nuke_path)
                    nuke_dir = os.path.dirname(self.nuke_path)
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                          universal_newlines=True, env=env, cwd=nuke_dir)
                    stdout, stderr = proc.communicate()
                    returncode = proc.returncode
                    output = (stdout + stderr).strip()
                if returncode != 0:
                    errors.append(f"Error rendering {node['name']}: {output}")
            except Exception as e:
                errors.append(f"Error rendering {node['name']}: {str(e)}")
        progress.setValue(len(nodes))
        if errors:
            QtWidgets.QMessageBox.warning(self, "Render Issues", "Some renders had errors:\n\n" + "\n\n".join(errors))
        else:
            QtWidgets.QMessageBox.information(self, "Success", "Finished rendering all selected nodes!")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = BatchRenderTool()
    window.show()
    sys.exit(app.exec_())
