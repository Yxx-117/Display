"""Docsify 知识库本地维护工具（交互式菜单）。

把两件高频操作合并到一个入口：
  1. 更新目录导航（调用 update_docsify_readmes.py）
  2. 本地调试（启动本地静态服务预览 docsify_root）

用法：
    python dev.py
脚本通过自身路径定位仓库根目录，因此在任意目录下运行都可以，例如：

    cd docsify_root
    python ..\\dev.py
"""

from __future__ import annotations

import subprocess
import sys
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCSIFY_ROOT = ROOT / "docsify_root"
NAV_SCRIPT = ROOT / "update_docsify_readmes.py"

DEFAULT_PORT = 3000
MAX_PORT_TRY = 20

MENU = """
========================================
  Docsify 知识库维护工具
========================================
  站点目录: {site_dir}

  1. 更新目录导航
  2. 本地调试（启动本地服务）
  q. 退出
"""


# ---------------------------------------------------------------- 功能 1


def update_navigation() -> bool:
    print("\n[1] 正在更新目录导航 ...\n")
    if not NAV_SCRIPT.is_file():
        print(f"未找到导航脚本：{NAV_SCRIPT}\n")
        return False

    result = subprocess.run([sys.executable, str(NAV_SCRIPT)], cwd=str(ROOT))
    if result.returncode == 0:
        print("\n导航更新完成。\n")
        return True

    print(f"\n导航更新失败，退出码：{result.returncode}\n")
    return False


# ---------------------------------------------------------------- 功能 2


def start_server(port: int):
    """在后台线程启动静态服务，返回 (server, url)。端口被占用时自动顺延。"""
    handler = partial(SimpleHTTPRequestHandler, directory=str(DOCSIFY_ROOT))

    for _ in range(MAX_PORT_TRY):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            port += 1
    else:
        return None, None

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}/"


def run_local_server() -> None:
    server, url = start_server(DEFAULT_PORT)
    if server is None:
        print(f"\n端口 {DEFAULT_PORT} 及其后 {MAX_PORT_TRY} 个端口均被占用，无法启动服务。\n")
        return

    print(f"\n[2] 本地服务已启动：{url}")
    print("    正在打开浏览器 ...")
    try:
        webbrowser.open(url)
    except Exception:  # 打开失败不影响服务本身
        print("    浏览器打开失败，请手动访问上面的地址。")

    print("\n    服务运行中（下方会输出访问日志，可据此排查 404）")
    print("    输入 q 并回车停止服务，返回上级菜单\n")

    while True:
        try:
            command = input("服务运行中 [q] 停止> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            command = "q"
        if command in {"q", "quit", "exit", ""}:
            break
        print("    无法识别的输入，停止服务请输入 q。")

    server.shutdown()
    server.server_close()
    print("\n本地服务已停止。\n")


# ---------------------------------------------------------------- 主流程


def main() -> int:
    if not DOCSIFY_ROOT.is_dir():
        print(f"未找到站点目录：{DOCSIFY_ROOT}")
        return 1

    while True:
        print(MENU.format(site_dir=DOCSIFY_ROOT))
        try:
            choice = input("请输入选项 (1/2/q): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n已退出。")
            return 0

        if choice == "":
            continue
        if choice == "1":
            update_navigation()
        elif choice == "2":
            run_local_server()
        elif choice in {"q", "quit", "exit"}:
            print("已退出。")
            return 0
        else:
            print("无法识别的选项，请重新输入。\n")


if __name__ == "__main__":
    raise SystemExit(main())
