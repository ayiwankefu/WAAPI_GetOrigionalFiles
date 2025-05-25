#Author Leafxie
from waapi import WaapiClient, CannotConnectToWaapiException
import os
import filecmp
import shutil
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem, QProgressBar, QPushButton, QLabel
)
from PyQt5.QtCore import Qt, QUrl, QMimeData
from PyQt5.QtGui import  QGuiApplication
from PyQt5.Qt import QAbstractItemView
import librosa
import librosa.display
import subprocess

def get_project_path(client):
    args = {
        "waql": "\"\\\""
    }
    options = {
        "return": ["filePath"]
    }
    return client.call("ak.wwise.core.object.get", args, options=options)["return"][0]["filePath"]

def get_original_wav_files(client):
    originalWavFilesPath = []
    _selectedObjectPath = []
    get_selectedObjects_opt = {
        "return": ["path", "type", "originalWavFilePath"]
    }
    selectedObjects = client.call("ak.wwise.ui.getSelectedObjects", options=get_selectedObjects_opt)["objects"]

    for i in range(len(selectedObjects)):
        _selectedObjectPath.append(selectedObjects[i]["path"])
        separator = "\",\""
        selectedObjectPath = separator.join(_selectedObjectPath)
        WAQL_PATH = f"$\"{selectedObjectPath}\"  select descendants distinct where type = \"AudioFileSource\""
        obj_get_args = {
            "waql": WAQL_PATH
        }
        obj_get_options = {
            "return": ["sound:originalWavFilePath"]
        }
        _originalWavFilePath = client.call("ak.wwise.core.object.get", obj_get_args, options=obj_get_options)[
            "return"]
        for i in range(len(_originalWavFilePath)):
            originalWavFilesPath.append(_originalWavFilePath[i]["sound:originalWavFilePath"])
    originalWavFilesPath = list(set(originalWavFilesPath))  # 去重复项
    originalWavFilesPath.sort()  # 重新排列
    originalWavFilesPath = [p for p in originalWavFilesPath if os.path.exists(p)]  # 确保文件存在
    return originalWavFilesPath

class CopyProgressBar(QWidget):
    def __init__(self, total, width=700, height=10, parent=None):
        super().__init__(parent)
        self.setWindowTitle("拷贝音频文件到WAAPI_CopiedWavFiles")
        layout = QVBoxLayout(self)
        self.label = QLabel("正在拷贝音频文件...", self)
        layout.addWidget(self.label)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setFixedHeight(height)
        self.progress_bar.setFixedWidth(width)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)
    # 重写showEvent方法以居中显示窗口
    def showEvent(self, event):
        # 居中显示窗口
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        size = self.geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        super().showEvent(event)

def compare_and_copy_files(file_paths, destination_dir, progress_bar=None):
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    total = len(file_paths)
    destination_files_path = []
    for idx, path in enumerate(file_paths):
        filename = os.path.basename(path)  # 获取单个文件名
        destination_path = os.path.join(destination_dir, filename)  # 设定单个文件拷贝路径
        if os.path.exists(destination_path):
            # Compare existing file and source file
            if not filecmp.cmp(path, destination_path):
                # Files are different, add a suffix and copy
                suffix = 1
                base, ext = os.path.splitext(filename)
                new_filename = f"{base}_{suffix}{ext}"
                new_destination_path = os.path.join(destination_dir, new_filename)
                while os.path.exists(new_destination_path):
                    suffix += 1
                    new_filename = f"{base}_{suffix}{ext}"
                    new_destination_path = os.path.join(destination_dir, new_filename)
                destination_files_path.append(new_destination_path)
                shutil.copy(path, new_destination_path)
                print(f"文件 '{path}' 拷贝成功，命名变更为 '{new_filename}'")
            else:
                # Files are identical, skip copying
                destination_files_path.append(destination_path)
                print(f"文件 '{filename}' 已存在且完全相同，跳过拷贝")
        else:
            # File does not exist, copy directly
            destination_files_path.append(destination_path)
            shutil.copy(path, destination_path)
            print(f"文件 '{path}' 拷贝成功")
        # 更新进度条
        if progress_bar is not None:
            progress_bar.setValue(idx + 1)
            QApplication.processEvents()
    return destination_files_path

class MainWindow(QWidget):
    def __init__(self, wav_files, folder_to_place):
        super().__init__()
        self.wav_files = wav_files
        self.folder_to_place = folder_to_place
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Wwise 原始音频文件浏览器")
        layout = QVBoxLayout(self)
        # 按钮区域
        btn_layout = QHBoxLayout()
        self.btn_open_folder = QPushButton("打开文件夹")
        self.btn_copy_all = QPushButton("复制列表音频文件到剪切板")
        btn_layout.addWidget(self.btn_open_folder)
        btn_layout.addWidget(self.btn_copy_all)
        layout.addLayout(btn_layout)

        self.btn_open_folder.clicked.connect(self.open_folder)
        self.btn_copy_all.clicked.connect(self.copy_all_files_to_clipboard)

        self.table = QTableWidget(len(self.wav_files), 2)
        self.table.setHorizontalHeaderLabels(["文件名", "文件时长(秒)", "波形"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.ContiguousSelection)  # 支持连续多选
        for i, path in enumerate(self.wav_files):
            # 文件名
            item_name = QTableWidgetItem(os.path.basename(path))
            item_name.setData(Qt.UserRole, path)
            self.table.setItem(i, 0, item_name)
            # 文件时长
            try:
                duration = librosa.get_duration(filename = path)
                item_duration = QTableWidgetItem(f"{duration:.3f}")
            except Exception as e:
                item_duration = QTableWidgetItem("读取失败")
            self.table.setItem(i, 1, item_duration)
        self.table.setColumnWidth(0, 500)
        self.table.setColumnWidth(1, 100)
        layout.addWidget(self.table)

    def open_folder(self):
        path = os.path.normpath(self.folder_to_place)
        if sys.platform.startswith('win'):
            os.startfile(path)
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])

    def copy_all_files_to_clipboard(self):
        # 1. 检查文件是否存在
        existing_files = [os.path.abspath(f) for f in self.wav_files if os.path.exists(f)]
        if not existing_files:
            print("错误：没有找到文件！")
            return
        # 2. 用 QMimeData 设置剪贴板为文件列表（推荐方式，兼容性好）
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(f) for f in existing_files]
        mime_data.setUrls(urls)
        QGuiApplication.clipboard().setMimeData(mime_data)
        print(f"已复制 {len(existing_files)} 个文件到剪贴板，可 Ctrl+V 粘贴！")
    def copy_table_selection(self):
        selection = self.table.selectedRanges()
        if not selection:
            return
        s = ""
        for r in selection:
            for row in range(r.topRow(), r.bottomRow() + 1):
                row_data = []
                for col in range(r.leftColumn(), r.rightColumn() + 1):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                s += "\t".join(row_data) + "\n"
        QGuiApplication.clipboard().setText(s.strip())

if __name__ == "__main__":
    try:
        client = WaapiClient()
    except CannotConnectToWaapiException:
        print("Could not connect to Waapi: Is Wwise running and Wwise Authoring API enabled?")
        sys.exit(1)
    else:
        project_path = get_project_path(client)#获取Wwise工程路径
        project_dir = os.path.dirname(project_path)
        folder_to_place = os.path.join(project_dir, "WAAPI_CopiedWavFiles")
        app = QApplication(sys.argv)
        originalWavFilesPath = get_original_wav_files(client)  # 获取原始Wav文件路径

        # 独立进度条窗口
        copy_progress = CopyProgressBar(len(originalWavFilesPath))
        copy_progress.show()
        files_in_WAAPI_CopiedWavFiles = compare_and_copy_files(
            originalWavFilesPath, folder_to_place, progress_bar=copy_progress.progress_bar
        )
        copy_progress.close()

        window = MainWindow(files_in_WAAPI_CopiedWavFiles, folder_to_place)
        window.resize(700, 600)
        window.show()
        sys.exit(app.exec_())
