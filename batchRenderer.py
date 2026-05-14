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
            with open(script_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            print(f"[ERROR] Could not open file: {e}")
            return []

        blocks = content.split("Write {")

        root_first, root_last = self._parse_root_frame_range(content)

        write_nodes = []
        for block in blocks[1:]:
            end_idx = self._find_block_end(block)
            if end_idx != -1:
                block = block[:end_idx]
            name = self._extract_attribute(block, "name") or "Write"
            output_file = self._extract_attribute(block, "file") or ""
            first_frame = self._parse_int(self._extract_attribute(block, "first"), root_first)
            last_frame = self._parse_int(self._extract_attribute(block, "last"), root_last)
            write_nodes.append({
                'name': name,
                'file': output_file,
                'first_frame': first_frame,
                'last_frame': last_frame,
            })
        return write_nodes

    def _parse_root_frame_range(self, content):
        parts = content.split("Root {")
        if len(parts) < 2:
            return 1, 1
        root_block = parts[1]
        end_idx = self._find_block_end(root_block)
        if end_idx != -1:
            root_block = root_block[:end_idx]
        first = self._parse_int(self._extract_attribute(root_block, "first_frame"), 1)
        last = self._parse_int(self._extract_attribute(root_block, "last_frame"), 1)
        return first, last

    def _find_block_end(self, text):
        depth = 1
        for i, ch in enumerate(text):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def _extract_attribute(self, text, attr_name):
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(f"{attr_name} "):
                value = line.split(" ", 1)[1]
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                return value
        return None

    def _parse_int(self, value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


class BatchRenderTool(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nuke Batch Renderer")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        self.nuke_files = []
        self.node_models = []
        self.parser = NukeScriptParser()
        self.nuke_path = ""
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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Render", "Name", "Start", "End", "Output Path", "Script File"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
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
            "Nuke Scripts (*.nk);;All Files (*.*)"
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
                    'first_frame': node['first_frame'],
                    'last_frame': node['last_frame'],
                })
        self.update_table()

        if not self.node_models:
            QtWidgets.QMessageBox.warning(
                self, "No Write Nodes Found",
                "No Write nodes were found in the selected script(s).\n"
                "Make sure the files are valid Nuke scripts containing Write nodes."
            )

    def update_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.node_models))
        for i, m in enumerate(self.node_models):
            chk_widget = QtWidgets.QWidget()
            chk_layout = QtWidgets.QHBoxLayout(chk_widget)
            chk_layout.addWidget(m['chk'])
            chk_layout.setAlignment(QtCore.Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)

            name_item = QtWidgets.QTableWidgetItem(m['name'])
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)

            start_item = QtWidgets.QTableWidgetItem(str(m['first_frame']))
            start_item.setTextAlignment(QtCore.Qt.AlignCenter)

            end_item = QtWidgets.QTableWidgetItem(str(m['last_frame']))
            end_item.setTextAlignment(QtCore.Qt.AlignCenter)

            path_item = QtWidgets.QTableWidgetItem(m['file'])
            path_item.setFlags(path_item.flags() & ~QtCore.Qt.ItemIsEditable)

            script_item = QtWidgets.QTableWidgetItem(os.path.basename(m['script']))
            script_item.setFlags(script_item.flags() & ~QtCore.Qt.ItemIsEditable)

            self.table.setCellWidget(i, 0, chk_widget)
            self.table.setItem(i, 1, name_item)
            self.table.setItem(i, 2, start_item)
            self.table.setItem(i, 3, end_item)
            self.table.setItem(i, 4, path_item)
            self.table.setItem(i, 5, script_item)
        self.table.blockSignals(False)

    def _sync_frame_range_from_table(self):
        for i, m in enumerate(self.node_models):
            try:
                m['first_frame'] = int(self.table.item(i, 2).text())
            except (ValueError, AttributeError):
                pass
            try:
                m['last_frame'] = int(self.table.item(i, 3).text())
            except (ValueError, AttributeError):
                pass

    def _build_render_cmd(self, node):
        cmd = [self.nuke_path]
        cmd.extend(['-F', f"{node['first_frame']}-{node['last_frame']}", '-i', '-X', node['name'], node['script']])
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
        self._sync_frame_range_from_table()
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
            progress.setLabelText(
                f"Rendering {node['name']} "
                f"(frames {node['first_frame']}-{node['last_frame']}) "
                f"from {os.path.basename(node['script'])}..."
            )
            try:
                returncode, output = self._run_nuke(self._build_render_cmd(node))
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
