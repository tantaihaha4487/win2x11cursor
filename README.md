# win2x11cursor

Convert a Windows cursor theme folder, archive, or download URL with `.ani` / `.cur` files into an installable X11/Xcursor theme.

`win2x11cursor` is a small Python CLI that uses `win2xcur` for the cursor parsing and Xcursor writing work.

## What it does

- Reads a Windows theme folder, archive, or `install.inf`
- Converts the cursors into an Xcursor theme
- Writes a standard Linux theme layout:
  - `index.theme`
  - `cursors/`
- Generates broad Xcursor aliases for better app compatibility
- Adds mappings for the extra Windows roles in this theme:
  - `Pin` -> `color-picker`
  - `Person` -> `person`

## Requirements

- Python 3.10+
- `win2xcur`
- ImageMagick available on the system

Optional archive tools:

- `.zip` and tar-family archives work with the Python standard library
- `.rar` needs `unrar` or `bsdtar`
- `.7z` and `.cab` need `bsdtar`

On Arch Linux that usually means `python-win2xcur` and `imagemagick`.

## Install

Install from the current checkout:

```bash
pip install .
```

Or run it directly from a checkout during development:

```bash
pip install -e .
```

## Arch Linux

This repo includes a `python-win2x11cursor-git` `PKGBUILD` for AUR-style packaging.

```bash
makepkg -si
```

## Usage

`source` can be a theme folder, `install.inf`, local archive, or direct HTTP(S) download URL.

Convert a theme folder named `MyCursorTheme` into `build/MyCursorTheme`:

```bash
win2x11cursor MyCursorTheme
```

Convert a local archive:

```bash
win2x11cursor MyCursorTheme.zip
```

Convert and install straight from an upstream download URL:

```bash
win2x11cursor https://example.com/MyCursorTheme.zip --install --force
```

Choose a different output root:

```bash
win2x11cursor MyCursorTheme --output out
```

Override the output theme folder name:

```bash
win2x11cursor MyCursorTheme --theme-dir MyCursorTheme-X11
```

Replace an existing generated theme:

```bash
win2x11cursor MyCursorTheme --force
```

Convert and install to `~/.local/share/icons`:

```bash
win2x11cursor MyCursorTheme --install --force
```

Show CLI help:

```bash
win2x11cursor --help
```

## Generated theme layout

Example output:

```text
build/
`-- MyCursorTheme/
    |-- cursors/
    |   |-- default
    |   |-- help
    |   |-- progress
    |   |-- wait
    |   |-- crosshair
    |   |-- text
    |   |-- pencil
    |   |-- not-allowed
    |   |-- size_ver
    |   |-- size_hor
    |   |-- size_fdiag
    |   |-- size_bdiag
    |   |-- fleur
    |   |-- center_ptr
    |   |-- pointer
    |   |-- color-picker
    |   `-- person
    `-- index.theme
```

The CLI also creates many common aliases like `left_ptr`, `hand2`, `xterm`, `watch`, `sb_v_double_arrow`, `fd_double_arrow`, and more.

## Install on Linux

If you used `--install`, the theme is already copied into:

```text
~/.local/share/icons/<theme-name>
```

If you only generated the files, copy the theme directory manually into `~/.local/share/icons/`.

Then select the theme by directory name.

### X11

Add this to `~/.Xresources`:

```text
Xcursor.theme: MyCursorTheme
Xcursor.size: 24
```

Then reload X resources or restart the session.

### GNOME

```bash
gsettings set org.gnome.desktop.interface cursor-theme 'MyCursorTheme'
```

### KDE Plasma

```bash
plasma-apply-cursortheme MyCursorTheme
```

### Sway

```text
seat * xcursor_theme MyCursorTheme 24
```

### Hyprland

```text
exec = hyprctl setcursor MyCursorTheme 24
```

## Notes

- The theme name written into `index.theme` matches the generated folder name for safer Xcursor lookup.
- The human-readable Windows source name is preserved in the `Comment` field.
- If your desktop environment caches cursors, log out and back in after switching themes.
