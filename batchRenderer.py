import os
import sys
import subprocess
from PyQt5 import QtWidgets, QtCore, QtGui

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
        self.table.setHorizontalHeaderLabels(["Render", "Name", "Path", "Script File"])
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
        file_filter = "Nuke Location (nuke*.exe);;All Files (*.*)" if sys.platform == "win32" else "All Files (*.*)"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Nuke Location", initial_dir, file_filter)
        if path:
            self.nuke_path = path
            self.nuke_path_edit.setText(path)

    def add_nuke_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Nuke Script Files", "", "Nuke Files (*.nk);;All Files (*.*)")
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
        self.node_models = []
        order = 1
        for script_file in self.nuke_files:
            nodes = self.parser.parse_nuke_file(script_file)
            for node in nodes:
                self.node_models.append({
                    'name': node['name'],
                    'file': node['file'],
                    'script': script_file,
                    'order': order,
                    'chk': QtWidgets.QCheckBox()
                })
                self.node_models[-1]['chk'].setChecked(True)
                order += 1
        self.update_table()

    def update_table(self):
        self.table.setRowCount(len(self.node_models))
        for i, m in enumerate(self.node_models):
            chk = m['chk']
            w = QtWidgets.QWidget()
            l = QtWidgets.QHBoxLayout(w)
            l.addWidget(chk)
            l.setAlignment(QtCore.Qt.AlignCenter)
            l.setContentsMargins(0, 0, 0, 0)
            name = QtWidgets.QTableWidgetItem(m['name'])
            path = QtWidgets.QTableWidgetItem(m['file'])
            path.setFlags(path.flags() & ~QtCore.Qt.ItemIsEditable)
            script = QtWidgets.QTableWidgetItem(os.path.basename(m['script']))
            script.setFlags(script.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setCellWidget(i, 0, w)
            self.table.setItem(i, 1, name)
            self.table.setItem(i, 2, path)
            self.table.setItem(i, 3, script)

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
            cmd = [self.nuke_path, '-X', node['name'], node['script']]
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                stdout, stderr = proc.communicate()
                if proc.returncode != 0:
                    errors.append(f"Error rendering {node['name']}: {stderr}")
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
