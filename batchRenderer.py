import glob
import os
import sys
import subprocess
from PyQt5 import QtWidgets, QtCore


def get_nuke_env(nuke_exe_path=None):
    env = os.environ.copy()

    user_profile = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    local_appdata = os.environ.get('LOCALAPPDATA', os.path.join(user_profile, 'AppData', 'Local'))
    homedrive, homepath = os.path.splitdrive(user_profile)

    foundry_token_path = os.path.join(local_appdata, 'Foundry', 'Tokens')
    if os.path.exists(foundry_token_path):
        env['FOUNDRY_LOGIN_TOKEN_PATH'] = foundry_token_path

    env['USERPROFILE'] = user_profile
    env['HOMEDRIVE'] = os.environ.get('HOMEDRIVE', homedrive)
    env['HOMEPATH'] = os.environ.get('HOMEPATH', homepath)
    env['LOCALAPPDATA'] = local_appdata
    env['APPDATA'] = os.environ.get('APPDATA', os.path.join(user_profile, 'AppData', 'Roaming'))

    if nuke_exe_path:
        nuke_dir = os.path.dirname(nuke_exe_path)
        if nuke_dir not in env.get('PATH', ''):
            env['PATH'] = nuke_dir + ';' + env.get('PATH', '')

    rlm_paths = [
        r'C:\ProgramData\The Foundry\RLM',
        r'C:\Program Files\The Foundry\RLM',
        r'C:\Program Files (x86)\The Foundry\RLM',
    ]
    existing_rlm = env.get('RLM_LICENSE', '')
    valid_rlm_paths = [p for p in rlm_paths if os.path.exists(p)]
    if existing_rlm:
        valid_rlm_paths.insert(0, existing_rlm)
    if valid_rlm_paths:
        env['RLM_LICENSE'] = ';'.join(valid_rlm_paths)

    env['foundry_LICENSE'] = env.get('RLM_LICENSE', '')

    for key in ['NUKE_LICENSE', 'NUKE_TRIAL', 'FOUNDRY_LICENSE', 'foundry_LICENSE']:
        if key in os.environ:
            env[key] = os.environ[key]

    return env


class NukeScriptParser:

    def parse_nuke_file(self, script_path):
        try:
            with open(script_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"Error parsing Nuke file: {e}")
            return []

        write_nodes = []
        for block in content.split("Write {")[1:]:
            end_idx = block.find("\n}")
            if end_idx != -1:
                block = block[:end_idx]
            name = self._extract_attribute(block, "name") or "Write"
            output_file = self._extract_attribute(block, "file") or ""
            write_nodes.append({'name': name, 'file': output_file})
        return write_nodes

    def _extract_attribute(self, text, attr_name):
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(f"{attr_name} "):
                value = line.split(" ", 1)[1]
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                return value
        return None


class BatchRenderTool(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
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
        nuke_path_layout.addWidget(QtWidgets.QLabel("Nuke Location:"))
        self.nuke_path_edit = QtWidgets.QLineEdit()
        nuke_path_layout.addWidget(self.nuke_path_edit)
        self.nuke_path_btn = QtWidgets.QPushButton("Browse...")
        self.nuke_path_btn.clicked.connect(self.browse_nuke_executable)
        nuke_path_layout.addWidget(self.nuke_path_btn)
        main_layout.addLayout(nuke_path_layout)

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
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Render", "Name", "Output Path", "Script File"])
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
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
        default_patterns = {
            "win32": "C:\\Program Files\\Nuke*",
            "darwin": "/Applications/Nuke*.app/Contents/MacOS",
            "linux": "/usr/local/Nuke*",
        }
        initial_dir = os.path.expanduser("~")
        pattern = default_patterns.get(sys.platform)
        if pattern:
            matches = glob.glob(pattern)
            if matches:
                initial_dir = matches[0]

        if sys.platform == "win32":
            file_filter = "Nuke Location (Nuke*.exe);;All Files (*.*)"
        else:
            file_filter = "All Files (*.*)"

        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Nuke Location", initial_dir, file_filter)
        if path:
            self.nuke_path = path
            self.nuke_path_edit.setText(path)

    def add_nuke_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Select Nuke Script Files", "",
            "Nuke Files (*.nk *.nknc);;Nuke Scripts (*.nk);;Nuke Non-Commercial (*.nknc);;All Files (*.*)"
        )
        for file_path in files:
            if file_path not in self.nuke_files:
                self.nuke_files.append(file_path)
                self.files_list.addItem(os.path.basename(file_path))

    def remove_nuke_file(self):
        selected = self.files_list.currentRow()
        if selected < 0:
            return
        file_path = self.nuke_files.pop(selected)
        self.files_list.takeItem(selected)
        self.node_models = [m for m in self.node_models if m['script'] != file_path]
        self.update_table()

    def import_write_nodes(self):
        if not self.nuke_files:
            QtWidgets.QMessageBox.warning(self, "Error", "No Nuke files selected!")
            return

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
            else:
                QtWidgets.QMessageBox.warning(
                    self, "Warning",
                    "Non-Commercial scripts may fail to render without '--nc' flag.\n"
                    "You can enable Non-Commercial Mode manually using the checkbox."
                )

        self.node_models = []
        for script_file in self.nuke_files:
            for node in self.parser.parse_nuke_file(script_file):
                chk = QtWidgets.QCheckBox()
                chk.setChecked(True)
                self.node_models.append({
                    'name': node['name'],
                    'file': node['file'],
                    'script': script_file,
                    'chk': chk,
                })
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

            path_item = QtWidgets.QTableWidgetItem(m['file'])
            path_item.setFlags(path_item.flags() & ~QtCore.Qt.ItemIsEditable)

            script_item = QtWidgets.QTableWidgetItem(os.path.basename(m['script']))
            script_item.setFlags(script_item.flags() & ~QtCore.Qt.ItemIsEditable)

            self.table.setCellWidget(i, 0, chk_widget)
            self.table.setItem(i, 1, name_item)
            self.table.setItem(i, 2, path_item)
            self.table.setItem(i, 3, script_item)

    def toggle_non_commercial(self, state):
        self.non_commercial_mode = (state == QtCore.Qt.Checked)

    def _build_render_cmd(self, node, script_path):
        cmd = [self.nuke_path]
        if self.non_commercial_mode:
            cmd.append('--nc')
        cmd.extend(['-i', '-X', node['name'], script_path])
        return cmd

    def _run_nuke(self, cmd):
        env = get_nuke_env(self.nuke_path)
        nuke_dir = os.path.dirname(self.nuke_path)
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, env=env, cwd=nuke_dir
        )
        stdout, stderr = proc.communicate()
        return proc.returncode, (stdout + stderr).strip()

    def _move_row(self, delta):
        sel = self.table.selectedIndexes()
        if not sel:
            return
        row = sel[0].row()
        target = row + delta
        if target < 0 or target >= len(self.node_models):
            return
        self.node_models[row], self.node_models[target] = self.node_models[target], self.node_models[row]
        self.update_table()
        self.table.selectRow(target)

    def move_up(self):
        self._move_row(-1)

    def move_down(self):
        self._move_row(1)

    def get_nodes_to_render(self):
        return [m for m in self.node_models if m['chk'].isChecked()]

    def do_render(self):
        if not self.nuke_path or not os.path.exists(self.nuke_path):
            QtWidgets.QMessageBox.warning(self, "Error", "Please select a valid Nuke Location!")
            return
        nodes = self.get_nodes_to_render()
        if not nodes:
            QtWidgets.QMessageBox.warning(self, "Error", "Select at least one node!")
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
                returncode, output = self._run_nuke(self._build_render_cmd(node, node['script']))
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
