from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from win2x11cursor.archive import extract_zip, is_archive_file
from win2x11cursor.source import (
    download_to_path,
    is_http_url,
    resolve_inf_path,
    resolve_source,
)


class FakeResponse:
    def __init__(self, data: bytes, *, url: str, filename: str | None = None) -> None:
        self._data = data
        self.url = url
        self._filename = filename
        self.headers = self

    def get_filename(self) -> str | None:
        return self._filename

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def make_zip_bytes(entries: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


class ResolveInfPathTests(unittest.TestCase):
    def test_finds_nested_inf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected = root / "theme" / "install.inf"
            expected.parent.mkdir(parents=True)
            expected.write_text("[DefaultInstall]\n", encoding="utf-8")

            self.assertEqual(resolve_inf_path(root), expected)

    def test_prefers_single_install_inf_when_multiple_inf_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            extra = root / "docs" / "notes.inf"
            expected = root / "theme" / "install.inf"
            extra.parent.mkdir(parents=True)
            expected.parent.mkdir(parents=True)
            extra.write_text("[Version]\n", encoding="utf-8")
            expected.write_text("[DefaultInstall]\n", encoding="utf-8")

            self.assertEqual(resolve_inf_path(root), expected)

    def test_errors_when_multiple_non_install_inf_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "one" / "alpha.inf"
            second = root / "two" / "beta.inf"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text("[Version]\n", encoding="utf-8")
            second.write_text("[Version]\n", encoding="utf-8")

            with self.assertRaisesRegex(
                RuntimeError, r"alpha\.inf, two/beta\.inf|one/alpha\.inf, two/beta\.inf"
            ):
                resolve_inf_path(root)


class SourceClassificationTests(unittest.TestCase):
    def test_detects_http_url(self) -> None:
        self.assertTrue(
            is_http_url(
                "https://vsthemes.org/en/cursors/anime/74484-furina-genshin-impact.html"
            )
        )
        self.assertFalse(is_http_url("/tmp/Furina.zip"))

    def test_detects_archive_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "Furina.zip"
            archive_path.write_bytes(
                make_zip_bytes({"Furina/install.inf": "[DefaultInstall]\n"})
            )
            inf_path = root / "install.inf"
            inf_path.write_text("[DefaultInstall]\n", encoding="utf-8")

            self.assertTrue(is_archive_file(archive_path))
            self.assertFalse(is_archive_file(inf_path))

    def test_resolves_directory_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected = root / "Furina" / "install.inf"
            expected.parent.mkdir(parents=True)
            expected.write_text("[DefaultInstall]\n", encoding="utf-8")

            with resolve_source(str(root)) as inf_path:
                self.assertEqual(inf_path, expected)

    def test_resolves_direct_inf_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inf_path = Path(temp_dir) / "install.inf"
            inf_path.write_text("[DefaultInstall]\n", encoding="utf-8")

            with resolve_source(str(inf_path)) as resolved:
                self.assertEqual(resolved, inf_path)


class ZipExtractionTests(unittest.TestCase):
    def test_extract_zip_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "Furina.zip"
            archive_path.write_bytes(
                make_zip_bytes(
                    {
                        "Furina/install.inf": "[DefaultInstall]\n",
                        "Furina/Normal.ani": "cursor",
                    }
                )
            )
            destination = root / "out"
            destination.mkdir()

            extract_zip(archive_path, destination)

            self.assertTrue((destination / "Furina" / "install.inf").is_file())
            self.assertTrue((destination / "Furina" / "Normal.ani").is_file())

    def test_rejects_zip_with_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "theme.zip"
            archive_path.write_bytes(
                make_zip_bytes({"/absolute/install.inf": "[DefaultInstall]\n"})
            )
            destination = root / "out"
            destination.mkdir()

            with self.assertRaisesRegex(ValueError, "absolute path"):
                extract_zip(archive_path, destination)


class ResolveSourceTests(unittest.TestCase):
    def test_extracts_local_zip_and_finds_nested_inf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "theme.zip"
            archive_path.write_bytes(
                make_zip_bytes({"wrapper/theme/install.inf": "[DefaultInstall]\n"})
            )

            with resolve_source(str(archive_path)) as inf_path:
                self.assertTrue(inf_path.exists())
                self.assertEqual(inf_path.name, "install.inf")
                self.assertEqual(inf_path.parent.name, "theme")

    def test_downloads_zip_from_url(self) -> None:
        archive_bytes = make_zip_bytes({"theme/install.inf": "[DefaultInstall]\n"})

        with patch(
            "win2x11cursor.source.urlopen",
            return_value=FakeResponse(
                archive_bytes,
                url="https://downloads.example/themes/theme.zip",
                filename="theme.zip",
            ),
        ):
            with resolve_source("https://example.com/theme") as inf_path:
                self.assertTrue(inf_path.exists())
                self.assertEqual(inf_path.name, "install.inf")

    def test_downloads_vsthemes_style_url_using_final_archive_name(self) -> None:
        archive_bytes = make_zip_bytes({"Furina/install.inf": "[DefaultInstall]\n"})

        with patch(
            "win2x11cursor.source.urlopen",
            return_value=FakeResponse(
                archive_bytes,
                url="https://downloads.example/vsthemes/Furina.zip",
            ),
        ):
            with resolve_source(
                "https://vsthemes.org/en/cursors/anime/74484-furina-genshin-impact.html"
            ) as inf_path:
                self.assertTrue(inf_path.exists())
                self.assertEqual(inf_path.name, "install.inf")

    def test_rejects_zip_with_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path = root / "theme.zip"
            archive_path.write_bytes(
                make_zip_bytes({"../escape/install.inf": "[DefaultInstall]\n"})
            )

            with self.assertRaisesRegex(ValueError, "unsafe path"):
                with resolve_source(str(archive_path)):
                    pass


class DownloadTests(unittest.TestCase):
    def test_download_uses_header_filename_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            with patch(
                "win2x11cursor.source.urlopen",
                return_value=FakeResponse(
                    b"zip-bytes",
                    url="https://downloads.example/files/random.bin",
                    filename="Furina.zip",
                ),
            ):
                target = download_to_path(
                    "https://vsthemes.org/en/cursors/anime/74484-furina-genshin-impact.html",
                    destination,
                )

            self.assertEqual(target.name, "Furina.zip")
            self.assertEqual(target.read_bytes(), b"zip-bytes")

    def test_download_uses_final_response_url_when_header_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            with patch(
                "win2x11cursor.source.urlopen",
                return_value=FakeResponse(
                    b"zip-bytes",
                    url="https://downloads.example/vsthemes/Furina.zip",
                ),
            ):
                target = download_to_path(
                    "https://vsthemes.org/en/cursors/anime/74484-furina-genshin-impact.html",
                    destination,
                )

            self.assertEqual(target.name, "Furina.zip")
            self.assertEqual(target.read_bytes(), b"zip-bytes")


if __name__ == "__main__":
    unittest.main()
