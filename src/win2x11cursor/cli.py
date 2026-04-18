from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .source import resolve_source
from .windows_theme import ROLE_NAMES, parse_windows_theme
from .xcursor_theme import (
    build_alias_groups,
    install_theme,
    prepare_output_dir,
    slugify,
    write_aliases,
    write_index_theme,
)


@dataclass(frozen=True)
class ConversionSummary:
    source: str
    inf_path: Path
    theme_dir_name: str
    theme_root: Path
    converted: list[tuple[str, str, int]]
    missing: list[str]
    install_path: Path | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="win2x11cursor",
        description="Convert a Windows cursor theme folder, archive, or URL into an installable Xcursor theme.",
    )
    parser.add_argument(
        "source",
        help="Path or HTTP(S) URL to a Windows cursor theme folder, archive, or install.inf file.",
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
        summary = convert_theme(args)
    except KeyboardInterrupt:
        parser.exit(130, "Interrupted by user\n")
    except Exception as exc:
        parser.exit(1, f"Error: {exc}\n")

    print_summary(summary)
    return 0


def convert_theme(args: argparse.Namespace) -> ConversionSummary:
    open_blob, to_x11 = load_runtime()

    with resolve_source(args.source) as inf_path:
        source_theme_name, cursors = parse_windows_theme(inf_path, open_blob)
        source_theme_name = (
            args.theme_name or source_theme_name or inf_path.parent.name
        ).strip()
        theme_dir_name = args.theme_dir or slugify(source_theme_name)
        theme_root = args.output.expanduser().resolve() / theme_dir_name
        cursor_root = theme_root / "cursors"

        prepare_output_dir(theme_root, force=args.force)
        cursor_root.mkdir(parents=True, exist_ok=True)

        converted, missing = write_cursor_theme(cursor_root, cursors, to_x11)
        if not converted:
            raise RuntimeError(f"No cursors were converted from {inf_path}")

        write_index_theme(
            path=theme_root / "index.theme",
            theme_dir_name=theme_dir_name,
            source_theme_name=source_theme_name,
            inherits=args.inherits,
            default_size=args.default_size,
        )

        install_path = None
        if args.install:
            install_path = install_theme(
                theme_root, args.install_root.expanduser(), args.force
            )

    return ConversionSummary(
        source=str(args.source),
        inf_path=inf_path,
        theme_dir_name=theme_dir_name,
        theme_root=theme_root,
        converted=converted,
        missing=missing,
        install_path=install_path,
    )


def load_runtime() -> tuple[Any, Any]:
    try:
        from win2xcur.parser import open_blob
        from win2xcur.writer import to_x11
    except ImportError as exc:
        raise RuntimeError(
            "Missing runtime dependency 'win2xcur'. Install the package and try again."
        ) from exc

    return open_blob, to_x11


def write_cursor_theme(
    cursor_root: Path,
    cursors: dict[str, Any],
    to_x11: Any,
) -> tuple[list[tuple[str, str, int]], list[str]]:
    converted: list[tuple[str, str, int]] = []
    missing: list[str] = []

    for role, names in build_alias_groups().items():
        cursor = cursors.get(role)
        if cursor is None:
            missing.append(role)
            continue

        canonical_name = names[0]
        output_path = cursor_root / canonical_name
        output_path.write_bytes(to_x11(cursor.frames))
        write_aliases(cursor_root, canonical_name, names[1:])
        converted.append((role, canonical_name, len(names) - 1))

    return converted, missing


def print_summary(summary: ConversionSummary) -> None:
    print(f"Source: {summary.source}")
    print(f"Resolved INF: {summary.inf_path}")
    print(f"Theme folder: {summary.theme_dir_name}")
    print(f"Output: {summary.theme_root}")
    print(f"Converted roles: {len(summary.converted)}")

    for role, canonical_name, alias_count in summary.converted:
        print(
            f"  - {ROLE_NAMES.get(role, role)} -> {canonical_name} (+{alias_count} aliases)"
        )

    if summary.missing:
        labels = ", ".join(ROLE_NAMES.get(role, role) for role in summary.missing)
        print(f"Missing roles: {labels}")

    if summary.install_path is not None:
        print(f"Installed to: {summary.install_path}")
