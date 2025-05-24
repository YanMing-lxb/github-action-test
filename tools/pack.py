'''
 =======================================================================
 ·······································································
 ·······································································
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 ·······································································
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2025-04-25 12:28:56 +0800
LastEditTime : 2025-05-21 14:04:00 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /RefrTruck-HeatLoad-Solver/tools/pack.py
Description  : 
 -----------------------------------------------------------------------
'''

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent  # 项目根目录
sys.path.append(str(BASE_DIR))  # 关键路径设置

from rich.theme import Theme
from rich.console import Console

from src.version import __project_name__, __version__, __team__, __description__

if sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ======================
# 主题与样式配置
# ======================
custom_theme = Theme({
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "info": "bold blue",
    "status": "bold cyan",
    "time": "bold magenta"
})
console = Console(theme=custom_theme)

# ======================
# 项目配置
# ======================
PROJECT_NAME = __project_name__
ENTRY_POINT = Path("src/__main__.py")
CONFIG_DIR = Path("src/config")
DATA_DIR = Path("src/assets")
ICON_FILE = Path("src/assets/logo.ico")
REQUIREMENTS = "requirements.txt"
VENV_NAME = "venv_rhs"


# ======================
# 工具函数
# ======================
def get_venv_tool(venv_name: str, tool_name: str) -> Path:
    """获取虚拟环境工具路径"""
    bin_dir = "Scripts" if os.name == "nt" else "bin"
    ext = ".exe" if os.name == "nt" else ""
    return Path(venv_name) / bin_dir / f"{tool_name}{ext}"

def format_duration(seconds: float) -> str:
    """格式化时间显示"""
    if seconds > 60:
        return f"{seconds // 60:.0f}m {seconds % 60:.1f}s"
    return f"{seconds:.2f}s"

def run_command(command: list, success_msg: str, error_msg: str, process_name: str = "执行命令") -> bool:
    """
    通用命令执行函数
    :param command: 要执行的命令列表
    :param success_msg: 成功时显示的消息（支持富文本样式）
    :param error_msg: 失败时的错误提示前缀
    :param process_name: 正在进行的操作名称（用于状态提示）
    :return: 执行是否成功
    """
    try:
        console.print(f"[dim]执行命令: {' '.join(command)}[/]")
        start_time = time.time()
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        with console.status(f"[status]正在{process_name}..."):  # 动态状态提示
            while True:
                output = process.stdout.readline()
                if not output and process.poll() is not None:
                    break
                if output:
                    console.print(f"[dim]{output.strip()}[/]")

        if process.returncode == 0:
            console.print(
                f"✓ {success_msg} "
                f"[time](耗时: {format_duration(time.time()-start_time)})[/]",
                style="success"
            )
            return True
            
        raise subprocess.CalledProcessError(
            process.returncode, 
            command, 
            f"退出码: {process.returncode}"
        )
        
    except subprocess.CalledProcessError as e:
        console.print(f"✗ {error_msg}: {e}", style="error")
        return False

# ======================
# 核心功能
# ======================
def pre_check() -> bool:
    """打包前环境检查"""
    check_items = {
        "Python版本": (sys.version_info >= (3,8), "需要Python 3.8+"),
        "入口文件": (ENTRY_POINT.exists(), f"缺失入口文件 {ENTRY_POINT}"),
        "依赖文件": (Path(REQUIREMENTS).exists(), f"缺失依赖文件 {REQUIREMENTS}"),
    }
    console.print("🔍 开始环境检查", style="status")
    all_ok = True
    for name, (condition, msg) in check_items.items():
        if not condition:
            console.print(f"✗ {name}检查失败: {msg}", style="error")
            all_ok = False
            
    return all_ok

def create_venv(venv_name: str = VENV_NAME) -> bool:
    """创建隔离的虚拟环境"""
    console.print("🌱 开始创建虚拟环境", style="status")
    command = [
        sys.executable,
        "-m", "venv",
        venv_name
    ]
    
    success = run_command(
        command=command,
        success_msg=f"虚拟环境 [bold]{venv_name}[/] 创建成功",
        error_msg="虚拟环境创建失败",
        process_name="创建虚拟环境"
    )
    
    if not success:
        console.print("⚠️ 建议检查：\n1. Python环境是否正常\n2. 磁盘空间是否充足\n3. 权限是否足够", style="warning")
        
    return success

def install_dependencies(venv_name: str = VENV_NAME) -> bool:
    """安装项目依赖"""
    pip_path = get_venv_tool(venv_name, "pip")
    
    if not pip_path.exists():
        console.print(f"✗ 找不到pip可执行文件: [underline]{pip_path}[/]", style="error")
        return False

    console.print("📦 开始安装依赖", style="status")
    
    return all([
        run_command(
            command=[str(pip_path), "install", "-r", REQUIREMENTS],
            success_msg="项目依赖安装完成",
            error_msg="项目依赖安装失败",
            process_name="安装项目依赖"
        ),
        run_command(
            command=[str(pip_path), "install", "pyinstaller"],
            success_msg="PyInstaller安装完成",
            error_msg="PyInstaller安装失败",
            process_name="安装PyInstaller"
        )
    ])

def run_pyinstaller(venv_name: str = VENV_NAME) -> bool:
    """flet pack 打包应用程序"""
    flet_path = get_venv_tool(venv_name, "flet")
    # 打包参数配置

    args = [
        str(flet_path),
        'pack',
        "-i", str(ICON_FILE.resolve()),
        "--add-data", f"{DATA_DIR.resolve()}:assets",
        "--add-data", f"{CONFIG_DIR.resolve()};config",
        "-n", PROJECT_NAME,
        "-D",
        "--product-version", __version__,
        "--file-version", __version__,
        "--company-name", __team__,
        "--copyright", __team__,
        "--file-description", PROJECT_NAME,
        str(ENTRY_POINT.resolve())
    ]
    return run_command(
        command=args,
        success_msg=f"应用程序打包成功 → [bold underline]dist/{PROJECT_NAME}[/]",
        error_msg="打包失败",
        process_name="打包应用程序"
    )

def verify_pack() -> bool:
    """验证打包结果"""
    exe_path = Path("dist") / PROJECT_NAME / (PROJECT_NAME + (".exe" if os.name == "nt" else ""))
    
    checks = [
        (exe_path.exists(), "可执行文件未生成"),
        (exe_path.stat().st_size > 1024*1024, "可执行文件大小异常（<1MB）")
    ]
    
    all_ok = True
    for condition, msg in checks:
        if not condition:
            console.print(f"✗ 验证失败: {msg}", style="error")
            all_ok = False
            
    return all_ok

def clean_up():
    """清理打包环境"""
    try:
        # if Confirm.ask("⚠️  确定要清理打包环境吗？", default=True):
        # 清理打包产物
        for artifact in ["build", "__pycache__", VENV_NAME]:
            if Path(artifact).exists():
                shutil.rmtree(artifact)
                console.print(f"✓ 删除打包产物: {artifact}", style="info")
                
        # 清理spec文件
        for spec_file in Path().glob("*.spec"):
            spec_file.unlink()
            console.print(f"✓ 删除spec文件: {spec_file}", style="info")
            
        console.print("✓ 环境清理完成", style="success")
        return True
    except Exception as e:
        console.print(f"✗ 清理失败: {e}", style="error")
        return False

# ======================
# 主流程
# ======================
if __name__ == "__main__":
    try:
        console.rule(f"[bold]🚀 {PROJECT_NAME} 打包系统[/]")
        
        if not pre_check():
            console.rule("[bold red]❌ 预检查失败，打包终止！[/]")
            sys.exit(1)

        success = all([
            create_venv(),
            install_dependencies(),
            run_pyinstaller(),
            verify_pack()
        ])

        if success:
            console.rule("[bold green]✅ 打包成功！[/]")
            console.print(f"生成的可执行文件位于：[bold underline]dist/{PROJECT_NAME}[/]")
            clean_up()
        else:
            console.rule("[bold red]❌ 打包失败！[/]")

    except PermissionError as e:
        console.print(f"✗ 权限错误: {e}", style="error")
        console.print("建议：尝试以管理员权限运行本脚本", style="warning")
    except FileNotFoundError as e:
        console.print(f"✗ 文件缺失: {e}", style="error")
    except Exception as e:
        console.rule("[bold red]💥 发生未捕获异常！[/]")
        console.print_exception(show_locals=True)