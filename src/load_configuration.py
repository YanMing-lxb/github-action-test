import os
import sys
import toml


def load_config(config_filename:str)->dict:
    """
    加载配置文件，支持开发环境和 PyInstaller 打包环境。
    :param config_filename: 配置文件名（相对于程序根目录）
    :return: 解析后的配置字典
    """
    # 动态获取资源路径
    if getattr(sys, 'frozen', False):  # 判断是否为 PyInstaller 打包的可执行文件
        base_path = sys._MEIPASS
        # 打包环境下，config 和 src 同级
        config_path = os.path.join(base_path, "config", config_filename)
    else:
        # 开发环境下，config 在 src 目录内部
        base_path = os.path.abspath(".")
        config_path = os.path.join(base_path, "src", "config", config_filename)

    print(f"正在尝试加载配置文件: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return toml.load(f)  # 使用 toml.load() 解析文件
    except FileNotFoundError:
        raise SystemExit(f"错误：配置文件未找到，请确认文件路径是否正确：{config_path}")