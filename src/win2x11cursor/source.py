from __future__ import annotations

from contextlib import ExitStack, contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from . import __version__
from .archive import extract_archive, is_archive_file


DOWNLOAD_TIMEOUT = 30
USER_AGENT = f"win2x11cursor/{__version__}"


@contextmanager
def resolve_source(source: str | Path) -> Iterator[Path]:
    raw_source = str(source)
    with ExitStack() as stack:
        if is_http_url(raw_source):
            download_root = Path(
                stack.enter_context(TemporaryDirectory(prefix="win2x11cursor-"))
            )
            local_source = download_to_path(raw_source, download_root)
        else:
            local_source = Path(raw_source).expanduser().resolve()

        if not local_source.exists():
            raise FileNotFoundError(f"Path not found: {local_source}")

        if local_source.is_file() and is_archive_file(local_source):
            extract_root = Path(
                stack.enter_context(TemporaryDirectory(prefix="win2x11cursor-"))
            )
            extract_archive(local_source, extract_root)
            yield resolve_inf_path(extract_root)
            return

        yield resolve_inf_path(local_source)


def is_http_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def download_to_path(url: str, destination: Path) -> Path:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
        filename = infer_download_name(
            getattr(response, "url", url), response.headers.get_filename()
        )
        target = destination / filename
        target.write_bytes(response.read())
    return target


def infer_download_name(url: str, header_name: str | None) -> str:
    if header_name:
        name = Path(unquote(header_name)).name
        if name:
            return name

    path_name = Path(unquote(urlsplit(url).path)).name
    return path_name or "downloaded-theme"


def resolve_inf_path(source: Path) -> Path:
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Path not found: {source}")

    if source.is_file():
        if source.suffix.casefold() != ".inf":
            raise ValueError(
                f"Expected a directory, archive, or .inf file, got: {source.name}"
            )
        return source

    direct_match = source / "install.inf"
    if direct_match.is_file():
        return direct_match

    inf_files = sorted(
        path
        for path in source.rglob("*")
        if path.is_file() and path.suffix.casefold() == ".inf"
    )
    if len(inf_files) == 1:
        return inf_files[0]

    install_inf_files = [
        path for path in inf_files if path.name.casefold() == "install.inf"
    ]
    if len(install_inf_files) == 1:
        return install_inf_files[0]
    if len(install_inf_files) > 1:
        return choose_install_inf(source, install_inf_files)

    if not inf_files:
        raise FileNotFoundError(f"No .inf file found in: {source}")

    names = ", ".join(str(path.relative_to(source)) for path in inf_files)
    raise RuntimeError(f"Multiple .inf files found in {source}: {names}")


def choose_install_inf(source: Path, candidates: list[Path]) -> Path:
    return min(candidates, key=lambda path: install_inf_sort_key(source, path))


def install_inf_sort_key(source: Path, path: Path) -> tuple[int, int, str]:
    relative_path = path.relative_to(source)
    parts = tuple(part.casefold() for part in relative_path.parts[:-1])
    prefers_windows = 0 if "windows" in parts else 1
    return prefers_windows, len(relative_path.parts), str(relative_path)
