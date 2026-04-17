# X11 Cursor Convertor

Convert a Windows cursor theme folder with `.ani` / `.cur` files into an installable X11/Xcursor theme.

This project ships a small Python CLI and uses `win2xcur` for the cursor parsing and Xcursor writing work.

## What it does

- Reads a Windows theme folder or `install.inf`
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
- ImageMagick available on the system

`convert` is already available in this environment, which is usually enough for `Wand` / `win2xcur` to work.

## Setup

Create the virtual environment:

```bash
python3 -m venv .venv
```

Install the app into the virtual environment:

```bash
.venv/bin/pip install -e .
```

## Usage

Convert a theme folder named `MyCursorTheme` into `build/MyCursorTheme`:

```bash
.venv/bin/x11-cursor-convertor MyCursorTheme
```

Choose a different output root:

```bash
.venv/bin/x11-cursor-convertor MyCursorTheme --output out
```

Override the output theme folder name:

```bash
.venv/bin/x11-cursor-convertor MyCursorTheme --theme-dir MyCursorTheme-X11
```

Replace an existing generated theme:

```bash
.venv/bin/x11-cursor-convertor MyCursorTheme --force
```

Convert and install to `~/.local/share/icons`:

```bash
.venv/bin/x11-cursor-convertor MyCursorTheme --install --force
```

Show CLI help:

```bash
.venv/bin/x11-cursor-convertor --help
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
