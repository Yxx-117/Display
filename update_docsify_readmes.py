"""扫描 docsify_root 目录树，自动生成 Docsify 导航文件。

设计要点：
- 仓库里不存导航生成物的"真相"，真相是目录树本身
- 作者只维护 .md 正文，导航一律由本脚本重建
- 生成链接统一使用站点根路径，并对路径做 URL 编码，
  规避中文目录名、空格、括号在静态托管上的 404 问题

用法：
    python update_docsify_readmes.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
DOCSIFY_ROOT = ROOT / "docsify_root"

README_NAME = "README.md"
SIDEBAR_NAME = "_sidebar.md"

# 站点信息，按你的实际情况修改
SITE_TITLE = "团队知识库"
SITE_DESC = "团队内部 Docsify 知识库，用于统一沉淀产品文档、技术资料与流程规范。"

# 不参与导航生成的目录
IGNORE_DIRS = {"img", "images", "assets", "vendor", ".git", ".github", "node_modules"}

# 目录名排序前缀，仅用于排序，展示时会被去掉
DIR_PREFIX_RE = re.compile(r"^\d+[_\-.]")

# 目录重命名映射：{旧目录名: 新目录名}，用于一次性统一历史命名
RENAME_MAP: dict[str, str] = {
    # "01_产品业务文档": "产品业务文档",
}


# ---------------------------------------------------------------- 基础遍历


def iter_md_files(directory: Path) -> Iterable[Path]:
    """列出目录下需要参与导航的 Markdown 文档（排除 README 与下划线开头的导航文件）。"""
    for path in sorted(directory.glob("*.md"), key=lambda p: p.name.lower()):
        if path.name.lower() == README_NAME.lower():
            continue
        if path.name.startswith("_"):
            continue
        yield path


def iter_subdirs(directory: Path) -> Iterable[Path]:
    """列出子目录，跳过图片、静态资源等目录。"""
    for path in sorted((p for p in directory.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
        if path.name in IGNORE_DIRS or path.name.startswith("."):
            continue
        yield path


def sort_key(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).lower()


def rename_directories() -> None:
    for old_name, new_name in RENAME_MAP.items():
        matches = sorted(DOCSIFY_ROOT.rglob(old_name), key=lambda p: len(p.parts), reverse=True)
        for path in matches:
            if not path.is_dir():
                continue
            target = path.with_name(new_name)
            if not target.exists():
                path.rename(target)
                print(f"[rename] {path.name} -> {new_name}")


def has_document_descendants(directory: Path) -> bool:
    """目录下（含子孙）是否存在可展示文档。"""
    if any(iter_md_files(directory)):
        return True
    return any(has_document_descendants(child) for child in iter_subdirs(directory))


def is_final_directory(directory: Path) -> bool:
    """叶子目录：自身直接包含文档。"""
    return any(iter_md_files(directory))


# ---------------------------------------------------------------- 名称与链接


def display_name(path: Path) -> str:
    """展示名：去掉排序用的数字前缀。"""
    name = path.stem if path.is_file() else path.name
    return DIR_PREFIX_RE.sub("", name)


def site_link(target: Path) -> str:
    """站点根路径链接，如 /01_产品业务文档/01_快速开始/README.md（已 URL 编码）。"""
    rel = target.relative_to(DOCSIFY_ROOT).as_posix()
    return "/" + quote(rel, safe="/")


def local_link(target: Path) -> str:
    """同目录内相对链接，如 ./快速开始.md（已 URL 编码）。"""
    return "./" + quote(target.name, safe="")


def write_text(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 各类 README


def write_final_dir_readme(directory: Path) -> None:
    """叶子目录索引：列出同目录文档。"""
    readme_path = directory / README_NAME
    files = list(iter_md_files(directory))

    lines = [
        f"# {display_name(directory)}",
        "",
        "> 本页用于汇总当前目录文档入口。",
        "",
        "## 文档列表",
        "",
    ]

    if files:
        lines.extend(f"- [{display_name(file)}]({local_link(file)})" for file in files)
    else:
        lines.append("- 当前目录暂无可展示文档。")

    write_text(readme_path, lines)


def write_directory_index(directory: Path) -> None:
    """中间层目录索引：列出子目录入口 + 自身文档。"""
    readme_path = directory / README_NAME
    child_dirs = [child for child in iter_subdirs(directory) if has_document_descendants(child)]
    child_files = list(iter_md_files(directory))

    lines = [
        f"# {display_name(directory)}",
        "",
        "> 本页用于汇总当前目录下的文档与子目录入口。",
        "",
        "## 文档列表",
        "",
    ]

    lines.extend(
        f"- [{display_name(child)}]({local_link(child / README_NAME)})" for child in child_dirs
    )
    lines.extend(f"- [{display_name(file)}]({local_link(file)})" for file in child_files)

    if not child_dirs and not child_files:
        lines.append("- 当前目录暂无可展示文档。")

    write_text(readme_path, lines)


def write_root_readme() -> None:
    """站点首页：按顶层分类全量展开目录与文档。"""
    top_dirs = [child for child in iter_subdirs(DOCSIFY_ROOT) if has_document_descendants(child)]

    lines = [
        f"# {SITE_TITLE}",
        "",
        f"> {SITE_DESC}",
        "",
        "## 首页导航",
        "",
    ]

    for top_dir in top_dirs:
        lines.append(f"### {display_name(top_dir)}")
        lines.append("")

        sub_dirs = sorted(
            (p for p in top_dir.rglob("*") if p.is_dir()),
            key=lambda p: sort_key(DOCSIFY_ROOT, p),
        )
        for directory in sub_dirs:
            if any(part in IGNORE_DIRS for part in directory.parts):
                continue
            readme = directory / README_NAME
            if readme.exists() and directory != top_dir:
                lines.append(f"- [{display_name(directory)}]({site_link(readme)})")
                for file in iter_md_files(directory):
                    lines.append(f"  - [{display_name(file)}]({site_link(file)})")

        lines.append("")

    lines.extend(
        [
            "## 维护说明",
            "",
            "- 本页与 `_sidebar.md` 均由 `update_docsify_readmes.py` 自动生成，请勿手工长期维护。",
            "- 新增或删除文档后，重新运行该脚本即可同步导航。",
        ]
    )

    write_text(DOCSIFY_ROOT / README_NAME, lines)


# ---------------------------------------------------------------- 侧边栏


def write_sidebar(max_depth: int = 2) -> None:
    """侧边栏：只展开到指定层级，更深层由目录内 README 承接，避免侧边栏过长。"""
    top_dirs = [child for child in iter_subdirs(DOCSIFY_ROOT) if has_document_descendants(child)]
    lines: list[str] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        for child in iter_subdirs(directory):
            if not has_document_descendants(child):
                continue
            readme = child / README_NAME
            indent = "  " * depth
            if readme.exists():
                lines.append(f"{indent}- [{display_name(child)}]({site_link(readme)})")
            else:
                lines.append(f"{indent}- {display_name(child)}")
            walk(child, depth + 1)

    for top_dir in top_dirs:
        readme = top_dir / README_NAME
        if readme.exists():
            lines.append(f"- [{display_name(top_dir)}]({site_link(readme)})")
        else:
            lines.append(f"- {display_name(top_dir)}")
        walk(top_dir, 2)

    write_text(DOCSIFY_ROOT / SIDEBAR_NAME, lines)


# ---------------------------------------------------------------- 入口


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 Docsify 导航文件")
    parser.add_argument(
        "--sidebar-depth",
        type=int,
        default=2,
        help="侧边栏展开层级，默认 2（顶层分类 + 一级子目录）",
    )
    args = parser.parse_args()

    if not DOCSIFY_ROOT.is_dir():
        print(f"未找到站点根目录：{DOCSIFY_ROOT}", file=sys.stderr)
        return 1

    rename_directories()

    for directory in sorted(
        (p for p in DOCSIFY_ROOT.rglob("*") if p.is_dir()),
        key=lambda p: sort_key(DOCSIFY_ROOT, p),
    ):
        if any(part in IGNORE_DIRS for part in directory.parts):
            continue
        if is_final_directory(directory):
            write_final_dir_readme(directory)

    for top_dir in iter_subdirs(DOCSIFY_ROOT):
        if has_document_descendants(top_dir):
            write_directory_index(top_dir)

    write_root_readme()
    write_sidebar(args.sidebar_depth)

    print("Docsify 导航已更新：")
    print(f"  - {DOCSIFY_ROOT / README_NAME}")
    print(f"  - {DOCSIFY_ROOT / SIDEBAR_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
