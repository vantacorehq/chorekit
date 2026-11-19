"""Sorts the files of a folder into subfolders, and can undo the last run."""

import json
import shutil
from datetime import datetime
from pathlib import Path

from chorekit.categories import CATEGORY_FOLDERS, get_category

LOG_NAME = ".chorekit_moves.json"


def unique_target_path(target_dir: Path, filename: str) -> Path:
    """If the name is taken in the target folder, returns name_1.ext, name_2.ext, ..."""
    target_path = target_dir / filename
    if not target_path.exists():
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix
    counter = 1
    while target_path.exists():
        target_path = target_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    return target_path


def _is_sorted_folder_name(name: str) -> bool:
    return name in CATEGORY_FOLDERS or (len(name) == 7 and name[4] == "-" and name[:4].isdigit() and name[5:].isdigit())


def _iter_files(folder: Path, recursive: bool):
    """Yields files to sort. In recursive mode, already sorted folders directly
    inside the target folder (Images, Documents, 2026-01, ...) are skipped."""
    if not recursive:
        for item in sorted(folder.iterdir()):
            if item.is_file() and item.name != LOG_NAME:
                yield item
        return

    for item in sorted(folder.rglob("*")):
        if not item.is_file() or item.name == LOG_NAME:
            continue
        relative = item.relative_to(folder)
        if len(relative.parts) > 1 and _is_sorted_folder_name(relative.parts[0]):
            continue
        yield item


def _bucket_name(item: Path, by: str) -> str:
    if by == "month":
        return datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m")
    return get_category(item.suffix)


def sort_folder(folder: Path, dry_run: bool = False, recursive: bool = False, by: str = "type", log=print):
    """Sorts files into subfolders. Returns (stats, moves).

    stats: {subfolder name: number of files}
    moves: [{"from": ..., "to": ...}, ...] with paths relative to the folder
    by: "type" (Images, Documents, ...) or "month" (2026-01, 2026-02, ...)
    """
    if by not in ("type", "month"):
        raise ValueError(f"Unknown sort mode: {by}")

    stats: dict = {}
    moves: list = []

    for item in list(_iter_files(folder, recursive)):
        bucket = _bucket_name(item, by)
        stats[bucket] = stats.get(bucket, 0) + 1

        if dry_run:
            log(f"[dry-run] {item.relative_to(folder)} -> {bucket}/")
            continue

        target_dir = folder / bucket
        target_dir.mkdir(exist_ok=True)
        target_path = unique_target_path(target_dir, item.name)

        try:
            shutil.move(str(item), str(target_path))
        except OSError as e:
            log(f"Could not move {item.name}: {e}")
            stats[bucket] -= 1
            continue

        moves.append(
            {
                "from": item.relative_to(folder).as_posix(),
                "to": target_path.relative_to(folder).as_posix(),
            }
        )
        log(f"{item.relative_to(folder)} -> {target_path.relative_to(folder)}")

    stats = {name: count for name, count in stats.items() if count > 0}

    if moves:
        (folder / LOG_NAME).write_text(json.dumps(moves, indent=2, ensure_ascii=False), encoding="utf-8")

    return stats, moves


def undo_last_sort(folder: Path, log=print):
    """Moves files back using the log of the last sort. Returns (restored, skipped)."""
    log_path = folder / LOG_NAME
    if not log_path.exists():
        raise FileNotFoundError(f"No undo log found in {folder}")

    moves = json.loads(log_path.read_text(encoding="utf-8"))
    restored = 0
    skipped = 0

    for move in reversed(moves):
        current = folder / move["to"]
        original = folder / move["from"]

        if not current.exists():
            log(f"Skipped (file is gone): {move['to']}")
            skipped += 1
            continue
        if original.exists():
            log(f"Skipped (original place is taken): {move['from']}")
            skipped += 1
            continue

        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(current), str(original))
        log(f"{move['to']} -> {move['from']}")
        restored += 1

    # remove subfolders that became empty
    for move in moves:
        parent = (folder / move["to"]).parent
        if parent != folder and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

    if skipped == 0:
        log_path.unlink()

    return restored, skipped
