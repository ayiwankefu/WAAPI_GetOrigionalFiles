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
    # print(project_path)
    project_dir = os.path.dirname(project_path)
    # print(project_dir)
    folder_to_place = os.path.join(project_dir, "WAAPI_CopiedWavFiles")
    # print(folder_to_place)
    # endregion

    # region 获取所选对象的原始音频文件路径
    get_selobjs_opt = {
        "return": ["path"]
    }
    _selobjs_PATH = client.call("ak.wwise.ui.getSelectedObjects", options=get_selobjs_opt)["objects"]
    selobjs_PATH = [value for subdict in _selobjs_PATH for key, value in subdict.items()]
    # pprint(selobjs_PATH)
    separator = "\",\""
    selobjs_PATH = separator.join(selobjs_PATH)
    # pprint(selobjs_PATH)
    WAQL_PATH = f"$\"{selobjs_PATH}\"  select descendants distinct where type = \"sound\""
    obj_get_args = {
        "waql": WAQL_PATH
    }
    obj_get_options = {
        "return": ["sound:originalWavFilePath"]
    }
    _origionalWavFilePath = client.call("ak.wwise.core.object.get", obj_get_args, options=obj_get_options)["return"]
    origionalWavFilePath = [value for subdict in _origionalWavFilePath for key, value in subdict.items()]
    origionalWavFilePath = list(set(origionalWavFilePath))  # 去重复项
    origionalWavFilePath.sort()  # 重新排列

    # pprint(origionalWavFilePath)

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


    compare_and_copy_files(origionalWavFilePath, folder_to_place)
