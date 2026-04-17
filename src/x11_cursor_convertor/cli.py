from __future__ import annotations

import argparse
import ntpath
import re
import shutil
from configparser import ConfigParser, ParsingError
from csv import DictReader
from io import StringIO
from pathlib import Path
from typing import Any, Iterable


ROLE_NAMES = {
    "arrow": "Normal",
    "help": "Help",
    "working": "Working",
    "wait": "Busy",
    "crosshair": "Precision",
    "text": "Text",
    "pen": "Handwriting",
    "unavailable": "Unavailable",
    "size_ns": "Vertical",
    "size_ew": "Horizontal",
    "size_nwse": "Diagonal1",
    "size_nesw": "Diagonal2",
    "move": "Move",
    "up_arrow": "Alternate",
    "link": "Link",
    "location": "Pin",
    "person": "Person",
}

INF_CURSOR_ORDER = [
    "arrow",
    "help",
    "working",
    "wait",
    "crosshair",
    "text",
    "pen",
    "unavailable",
    "size_ns",
    "size_ew",
    "size_nwse",
    "size_nesw",
    "move",
    "up_arrow",
    "link",
    "location",
    "person",
]

SCHEME_PREFIXES = (
    'hkcu,"control panel\\cursors\\schemes",',
    'hklm,"software\\microsoft\\windows\\currentversion\\control panel\\cursors\\schemes",',
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="x11-cursor-convertor",
        description="Convert a Windows cursor theme folder into an installable Xcursor theme.",
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Path to a Windows cursor theme folder or its install.inf file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("build"),
        help="Output directory where the generated theme folder will be created.",
    )
    parser.add_argument(
        "-n",
        "--theme-name",
        help="Override the source theme name before the output folder name is derived.",
    )
    parser.add_argument(
        "--theme-dir",
        help="Override the generated theme folder name directly.",
    )
    parser.add_argument(
        "--inherits",
        default="hicolor",
        help="Inherited cursor theme written into index.theme.",
    )
    parser.add_argument(
        "--default-size",
        type=int,
        default=24,
        help="Default cursor size written into index.theme.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Copy the generated theme into ~/.local/share/icons after conversion.",
    )
    parser.add_argument(
        "--install-root",
        type=Path,
        default=Path.home() / ".local/share/icons",
        help="Base directory used when --install is enabled.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Replace an existing output or install directory with the same theme name.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        convert_theme(args)
    except KeyboardInterrupt:
        parser.exit(130, "Interrupted by user\n")
    except Exception as exc:
        parser.exit(1, f"Error: {exc}\n")

    return 0


def convert_theme(args: argparse.Namespace) -> None:
    try:
        from win2xcur.parser import open_blob
        from win2xcur.writer import to_x11
    except ImportError as exc:
        raise RuntimeError(
            "Missing runtime dependencies. Activate .venv and run '.venv/bin/pip install -e .' first."
        ) from exc

    inf_path = resolve_inf_path(args.source)
    source_theme_name, cursors = parse_windows_theme(inf_path, open_blob)
    source_theme_name = (
        args.theme_name or source_theme_name or inf_path.parent.name
    ).strip()
    theme_dir_name = args.theme_dir or slugify(source_theme_name)
    theme_root = args.output.expanduser().resolve() / theme_dir_name
    cursor_root = theme_root / "cursors"

    prepare_output_dir(theme_root, force=args.force)
    cursor_root.mkdir(parents=True, exist_ok=True)

    alias_groups = build_alias_groups()
    converted: list[tuple[str, str, int]] = []
    missing: list[str] = []

    for role, names in alias_groups.items():
        cursor = cursors.get(role)
        if cursor is None:
            missing.append(role)
            continue

        canonical_name = names[0]
        output_path = cursor_root / canonical_name
        output_path.write_bytes(to_x11(cursor.frames))
        write_aliases(cursor_root, canonical_name, names[1:])
        converted.append((role, canonical_name, len(names) - 1))

    if not converted:
        raise RuntimeError(f"No cursors were converted from {inf_path}")

    write_index_theme(
        path=theme_root / "index.theme",
        theme_dir_name=theme_dir_name,
        source_theme_name=source_theme_name,
        inherits=args.inherits,
        default_size=args.default_size,
    )

    print(f"Source: {inf_path}")
    print(f"Theme folder: {theme_dir_name}")
    print(f"Output: {theme_root}")
    print(f"Converted roles: {len(converted)}")

    for role, canonical_name, alias_count in converted:
        print(
            f"  - {ROLE_NAMES.get(role, role)} -> {canonical_name} (+{alias_count} aliases)"
        )

    if missing:
        labels = ", ".join(ROLE_NAMES.get(role, role) for role in missing)
        print(f"Missing roles: {labels}")

    if args.install:
        install_path = install_theme(
            theme_root, args.install_root.expanduser(), args.force
        )
        print(f"Installed to: {install_path}")


def resolve_inf_path(source: Path) -> Path:
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Path not found: {source}")

    if source.is_file():
        if source.suffix.casefold() != ".inf":
            raise ValueError(f"Expected an .inf file, got: {source.name}")
        return source

    direct_match = source / "install.inf"
    if direct_match.is_file():
        return direct_match

    inf_files = sorted(
        path
        for path in source.iterdir()
        if path.is_file() and path.suffix.casefold() == ".inf"
    )
    if len(inf_files) == 1:
        return inf_files[0]

    if not inf_files:
        raise FileNotFoundError(f"No .inf file found in: {source}")

    names = ", ".join(path.name for path in inf_files)
    raise RuntimeError(f"Multiple .inf files found in {source}: {names}")


def parse_windows_theme(inf_path: Path, open_blob: Any) -> tuple[str, dict[str, Any]]:
    parser = ConfigParser(allow_no_value=True, strict=False)

    try:
        parser.read(inf_path, encoding="utf-8-sig")
    except ParsingError as exc:
        raise ValueError(str(exc)) from exc

    try:
        reg_sections = parser["DefaultInstall"]["AddReg"].split(",")
    except KeyError as exc:
        raise ValueError(
            f"Unable to find registry update section in INF: {exc}"
        ) from exc

    updates: list[str] = []
    for reg_section in reg_sections:
        section_name = reg_section.strip()
        try:
            updates.extend(list(parser[section_name]))
        except KeyError as exc:
            raise ValueError(
                f"Registry update section does not exist in INF: {section_name}"
            ) from exc

    scheme_updates = [
        update for update in updates if update.startswith(SCHEME_PREFIXES)
    ]
    if not scheme_updates:
        raise ValueError("No cursor installs found in INF")
    if len(scheme_updates) > 1:
        raise ValueError("Multiple cursor installs found in INF")

    strings = dict(parser["Strings"]) if "Strings" in parser else {}
    parsed = next(
        DictReader(
            StringIO(scheme_updates[0]),
            fieldnames=["root", "path", "name", "flags", "value"],
        )
    )

    theme_name = expand_registry_value(parsed["name"], strings)
    cursor_paths = expand_registry_value(parsed["value"], strings).split(",")
    files_by_name = {
        file.name.casefold(): file
        for file in inf_path.parent.iterdir()
        if file.is_file()
    }
    cursors: dict[str, Any] = {}

    for role, filename in zip(INF_CURSOR_ORDER, cursor_paths):
        if not filename:
            continue

        basename = ntpath.basename(filename)
        source_file = files_by_name.get(basename.casefold())
        if source_file is None:
            raise FileNotFoundError(f"Expected cursor file next to INF: {basename}")

        cursors[role] = open_blob(source_file.read_bytes())

    return theme_name, cursors


def expand_registry_value(text: str, strings: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if not name:
            return "%"
        return strings.get(name, match.group(0)).strip('"')

    return re.sub(r"%(\w*)%", replace, text)


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-._")
    return slug or "converted-cursor-theme"


def prepare_output_dir(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            raise FileExistsError(
                f"Output directory already exists: {path}. Use --force to replace it."
            )
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()


def build_alias_groups() -> dict[str, list[str]]:
    aliases = {
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
    return {role: dedupe(names) for role, names in aliases.items()}


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
