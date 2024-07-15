#Author Leafxie
from waapi import WaapiClient, CannotConnectToWaapiException
from pprint import pprint
import os
import filecmp
import shutil

try:
    client = WaapiClient()
except CannotConnectToWaapiException:
    print("Could not connect to Waapi: Is Wwise running and Wwise Authoring API enabled?")
else:

    # region 获取Wwise工程所在文件夹路径
    def get_project_path():
        args = {
            "waql": "\"\\\""
        }
        options = {
            "return": ["filePath"]
        }
        return client.call("ak.wwise.core.object.get", args, options=options)["return"][0]["filePath"]

    project_path = get_project_path()  # 获取Wwise工程路径
    project_dir = os.path.dirname(project_path)
    folder_to_place = os.path.join(project_dir, "WAAPI_CopiedWavFiles")
    # endregion

    # region 获取所选对象的原始音频文件路径
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
    #pprint(originalWavFilesPath)

    # endregion

    def compare_and_copy_files(file_paths, destination_dir):
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        for path in file_paths:
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
                    shutil.copy(path, new_destination_path)
                    print(f"文件 '{path}' 拷贝成功，命名变更为 '{new_filename}'")
                else:
                    # Files are identical, skip copying
                    print(f"文件 '{filename}' 已存在且完全相同，跳过拷贝")
            else:
                # File does not exist, copy directly
                shutil.copy(path, destination_path)
                print(f"文件 '{path}' 拷贝成功")


    compare_and_copy_files(originalWavFilesPath, folder_to_place)
    print("程序执行完成")