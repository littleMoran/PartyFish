# build.py
import subprocess
import sys
import os


def main():
    print("正在打包 PartyFish...")

    # 清理旧文件
    for item in ["build", "dist"]:
        if os.path.exists(item):
            import shutil

            shutil.rmtree(item)

    # 构建命令
    cmd = [
        sys.executable,  # 当前Python解释器
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--name",
        "PartyFish",
        "--windowed",
        "--onefile",
        "--icon",
        "666.ico",
        "--add-data",
        "666.ico;.",  # 这里的分号在Python中是安全的
        "--add-data",
        "resources;resources",
        "--collect-data",
        "rapidocr_onnxruntime",
        "--collect-all",
        "rapidocr_onnxruntime",
        "--collect-all",
        "onnxruntime",
        "--hidden-import",
        "rapidocr_onnxruntime",
        "--hidden-import",
        "onnxruntime",
        "--hidden-import",
        "cv2",
        "--hidden-import",
        "numpy",
        "--hidden-import",
        "PIL",
        "--hidden-import",
        "pynput",
        "--hidden-import",
        "ttkbootstrap",
        "--hidden-import",
        "mss",
        "--hidden-import",
        "yaml",
        "--hidden-import",
        "winsound",
        "--clean",
        "PartyFish.py",
    ]

    print("执行命令:", " ".join(cmd))

    # 执行打包
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n打包成功！")
        print("可执行文件: dist/PartyFish.exe")
    else:
        print("\n打包失败！")

    return result.returncode


if __name__ == "__main__":
    exit_code = main()
    input("\n按回车键退出...")
    sys.exit(exit_code)
