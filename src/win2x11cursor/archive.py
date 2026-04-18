from __future__ import annotations

import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable


RAR_SIGNATURES = (
    b"Rar!\x1a\x07\x00",
    b"Rar!\x1a\x07\x01\x00",
)
ARCHIVE_SUFFIXES = {".rar", ".7z", ".cab"}


def is_archive_file(path: Path) -> bool:
    if zipfile.is_zipfile(path) or tarfile.is_tarfile(path):
        return True

    suffixes = tuple(suffix.casefold() for suffix in path.suffixes)
    if suffixes and suffixes[-1] in ARCHIVE_SUFFIXES:
        return True

    return read_signature(path).startswith(RAR_SIGNATURES)


def read_signature(path: Path, size: int = 8) -> bytes:
    try:
        with path.open("rb") as handle:
            return handle.read(size)
    except OSError:
        return b""


def extract_archive(source: Path, destination: Path) -> None:
    if zipfile.is_zipfile(source):
        extract_zip(source, destination)
        return

    if tarfile.is_tarfile(source):
        extract_tar(source, destination)
        return

    suffixes = tuple(suffix.casefold() for suffix in source.suffixes)
    if suffixes and suffixes[-1] == ".rar":
        extract_rar(source, destination)
        return

    if suffixes and suffixes[-1] in {".7z", ".cab"}:
        extract_with_bsdtar(source, destination)
        return

    raise ValueError(
        f"Unsupported archive format: {source.name}. Supported formats: zip, rar, tar, tar.gz, tgz, tar.bz2, tar.xz, 7z, cab"
    )


def extract_zip(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        validate_archive_members(
            destination, (member.filename for member in archive.infolist())
        )
        archive.extractall(destination)


def extract_tar(source: Path, destination: Path) -> None:
    with tarfile.open(source) as archive:
        members = archive.getmembers()
        validate_archive_members(destination, (member.name for member in members))
        archive.extractall(destination)


def extract_rar(source: Path, destination: Path) -> None:
    for command in (
        ["unrar", "x", "-idq", "-o+", str(source), str(destination)],
        ["bsdtar", "-xf", str(source), "-C", str(destination)],
    ):
        if run_extractor(command, source):
            return

    raise RuntimeError("RAR extraction requires 'unrar' or 'bsdtar' in PATH")


def extract_with_bsdtar(source: Path, destination: Path) -> None:
    try:
        subprocess.run(
            ["bsdtar", "-xf", str(source), "-C", str(destination)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Archive extraction requires 'bsdtar' in PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            exc.stderr.strip() or f"Failed to extract archive: {source}"
        ) from exc


def run_extractor(command: list[str], source: Path) -> bool:
    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            exc.stderr.strip() or f"Failed to extract archive: {source}"
        ) from exc

    return True


def validate_archive_members(destination: Path, members: Iterable[str]) -> None:
    root = destination.resolve()
    for member in members:
        member_path = Path(member)
        if member_path.is_absolute():
            raise ValueError(f"Archive contains an absolute path: {member}")

        resolved = (root / member_path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Archive contains an unsafe path: {member}") from exc
