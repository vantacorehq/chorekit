"""Builds a report about a folder: files and size per category, largest files."""

import csv
import io
import json
from pathlib import Path

from chorekit.categories import get_category
from chorekit.sorter import LOG_NAME


def human_size(num_bytes: int) -> str:
    """1536 -> '1.5 KB'."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def build_report(folder: Path, recursive: bool = False, top: int = 5) -> dict:
    """Collects statistics about the files of a folder."""
    paths = folder.rglob("*") if recursive else folder.iterdir()
    files = [p for p in paths if p.is_file() and p.name != LOG_NAME]

    per_category: dict = {}
    sizes = []
    for path in files:
        size = path.stat().st_size
        category = get_category(path.suffix)
        entry = per_category.setdefault(category, {"name": category, "files": 0, "bytes": 0})
        entry["files"] += 1
        entry["bytes"] += size
        sizes.append((size, path.relative_to(folder).as_posix()))

    categories = sorted(per_category.values(), key=lambda c: (-c["bytes"], c["name"]))
    largest = [{"path": p, "bytes": s} for s, p in sorted(sizes, key=lambda x: (-x[0], x[1]))[:top]]

    return {
        "folder": str(folder),
        "total_files": len(files),
        "total_bytes": sum(s for s, _ in sizes),
        "categories": categories,
        "largest": largest,
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# Folder report: {report['folder']}",
        "",
        f"Files: {report['total_files']}, total size: {human_size(report['total_bytes'])}",
        "",
        "| Category | Files | Size |",
        "| --- | ---: | ---: |",
    ]
    for c in report["categories"]:
        lines.append(f"| {c['name']} | {c['files']} | {human_size(c['bytes'])} |")

    if report["largest"]:
        lines += ["", "Largest files:", ""]
        for i, f in enumerate(report["largest"], start=1):
            lines.append(f"{i}. {f['path']} ({human_size(f['bytes'])})")

    return "\n".join(lines) + "\n"


def render_csv(report: dict) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["category", "files", "bytes"])
    for c in report["categories"]:
        writer.writerow([c["name"], c["files"], c["bytes"]])
    return buffer.getvalue()


def render_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


RENDERERS = {"md": render_markdown, "csv": render_csv, "json": render_json}
