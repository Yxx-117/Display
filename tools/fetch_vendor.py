"""把 index.html 引用的 CDN 资源下载到 docsify_root/vendor/，并改写为本地引用。

目的：不再依赖外部 CDN，避免国内网络导致的样式丢失或白屏。

用法：
    python tools/fetch_vendor.py            # 本地化
    python tools/fetch_vendor.py --restore  # 还原为 CDN 引用
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCSIFY_ROOT = ROOT / "docsify_root"
INDEX_FILE = DOCSIFY_ROOT / "index.html"
VENDOR_NAME = "vendor"
BACKUP_FILE = INDEX_FILE.with_name("index.html.cdn.bak")

URL_RE = re.compile(r'(?P<attr>href|src)="(?P<url>https?://[^"]+)"')
TIMEOUT = 30


def download(url: str, dest: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        data = response.read()
    if not data:
        raise ValueError(f"下载内容为空：{url}")
    dest.write_bytes(data)
    print(f"[ok] {dest.name}  ({len(data) / 1024:.1f} KB)")


def localize() -> int:
    if not INDEX_FILE.exists():
        print(f"未找到 {INDEX_FILE}", file=sys.stderr)
        return 1

    html = INDEX_FILE.read_text(encoding="utf-8")
    urls = [m.group("url") for m in URL_RE.finditer(html)]
    if not urls:
        print("index.html 中没有可本地化的外部资源。")
        return 0

    vendor_dir = DOCSIFY_ROOT / VENDOR_NAME
    vendor_dir.mkdir(parents=True, exist_ok=True)

    if not BACKUP_FILE.exists():
        BACKUP_FILE.write_text(html, encoding="utf-8")
        print(f"[backup] {BACKUP_FILE.name}")

    failed: list[str] = []
    for url in dict.fromkeys(urls):
        filename = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
        if not filename:
            failed.append(url)
            continue
        try:
            download(url, vendor_dir / filename)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as exc:
            print(f"[fail] {url} -> {exc}", file=sys.stderr)
            failed.append(url)

    def replace(match: re.Match) -> str:
        url = match.group("url")
        filename = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
        if url in failed or not filename:
            return match.group(0)
        return f'{match.group("attr")}="{VENDOR_NAME}/{filename}"'

    new_html = URL_RE.sub(replace, html)
    INDEX_FILE.write_text(new_html, encoding="utf-8")

    print(f"\n已改写 {len(urls) - len(failed)}/{len(urls)} 个资源为本地引用。")
    if failed:
        print("以下资源仍使用 CDN，请检查网络或手动下载：", file=sys.stderr)
        for url in failed:
            print(f"  - {url}", file=sys.stderr)
        return 1
    return 0


def restore() -> int:
    if not BACKUP_FILE.exists():
        print("没有找到备份文件，无需还原。", file=sys.stderr)
        return 1
    INDEX_FILE.write_text(BACKUP_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    BACKUP_FILE.unlink()
    print("已还原为 CDN 引用。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Docsify 静态资源本地化")
    parser.add_argument("--restore", action="store_true", help="还原为 CDN 引用")
    args = parser.parse_args()
    return restore() if args.restore else localize()


if __name__ == "__main__":
    raise SystemExit(main())
