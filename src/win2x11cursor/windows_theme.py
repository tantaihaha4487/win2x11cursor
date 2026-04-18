from __future__ import annotations

import ntpath
import re
from configparser import ConfigParser, ParsingError
from csv import DictReader
from io import StringIO
from pathlib import Path
from typing import Any


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
