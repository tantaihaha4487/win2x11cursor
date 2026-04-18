from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Iterable


ALIAS_GROUPS = {
    "arrow": [
        "default",
        "arrow",
        "left_ptr",
        "top_left_arrow",
        "right_ptr",
        "top_left_corner",
        "top_right_corner",
        "bottom_left_corner",
        "bottom_right_corner",
        "left_side",
        "right_side",
        "top_side",
        "bottom_side",
        "sb_left_arrow",
        "sb_right_arrow",
        "sb_down_arrow",
    ],
    "help": ["help", "left_ptr_help", "question_arrow", "whats_this"],
    "working": ["progress", "left_ptr_watch", "half-busy"],
    "wait": ["wait", "watch", "clock"],
    "crosshair": ["crosshair", "cross", "tcross", "diamond_cross", "cell", "plus"],
    "text": ["text", "xterm", "ibeam"],
    "pen": ["pencil", "draft", "handwriting"],
    "unavailable": [
        "not-allowed",
        "forbidden",
        "no-drop",
        "dnd-no-drop",
        "circle",
        "crossed_circle",
    ],
    "size_ns": [
        "size_ver",
        "ns-resize",
        "n-resize",
        "s-resize",
        "sb_v_double_arrow",
        "v_double_arrow",
        "row-resize",
        "split_v",
        "double_arrow",
    ],
    "size_ew": [
        "size_hor",
        "ew-resize",
        "e-resize",
        "w-resize",
        "sb_h_double_arrow",
        "h_double_arrow",
        "col-resize",
        "split_h",
    ],
    "size_nwse": [
        "size_fdiag",
        "nwse-resize",
        "nw-resize",
        "se-resize",
        "bd_double_arrow",
    ],
    "size_nesw": [
        "size_bdiag",
        "nesw-resize",
        "ne-resize",
        "sw-resize",
        "fd_double_arrow",
    ],
    "move": ["fleur", "size_all", "all-scroll", "move", "grabbing", "closedhand"],
    "up_arrow": ["center_ptr", "up-arrow", "sb_up_arrow"],
    "link": ["pointer", "pointing_hand", "hand", "hand1", "hand2"],
    "location": ["color-picker", "pin", "location"],
    "person": ["person"],
}


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-._")
    return slug or "converted-cursor-theme"


def prepare_output_dir(path: Path, force: bool) -> None:
    if not path.exists():
        return

    if not force:
        raise FileExistsError(
            f"Output directory already exists: {path}. Use --force to replace it."
        )

    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return

    path.unlink()


def build_alias_groups() -> dict[str, list[str]]:
    return {role: dedupe(names) for role, names in ALIAS_GROUPS.items()}


def dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def write_aliases(
    cursor_root: Path, canonical_name: str, aliases: Iterable[str]
) -> None:
    source = cursor_root / canonical_name
    source_bytes = source.read_bytes()

    for alias in aliases:
        alias_path = cursor_root / alias
        try:
            alias_path.symlink_to(canonical_name)
        except OSError:
            alias_path.write_bytes(source_bytes)


def write_index_theme(
    *,
    path: Path,
    theme_dir_name: str,
    source_theme_name: str,
    inherits: str,
    default_size: int,
) -> None:
    path.write_text(
        "\n".join(
            [
                "[Icon Theme]",
                f"Name={theme_dir_name}",
                f"Comment=Converted from Windows cursor theme {source_theme_name}",
                f"Inherits={inherits}",
                "",
                "[Cursor Theme]",
                f"Size={default_size}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def install_theme(theme_root: Path, install_root: Path, force: bool) -> Path:
    install_root.mkdir(parents=True, exist_ok=True)
    destination = install_root / theme_root.name
    if destination.exists():
        if not force:
            raise FileExistsError(
                f"Install destination already exists: {destination}. Use --force to replace it."
            )
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()

    shutil.copytree(theme_root, destination, symlinks=True)
    return destination
