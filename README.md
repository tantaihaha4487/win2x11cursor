# win2x11cursor

Convert a Windows cursor theme folder, archive, or download URL into an installable X11/Xcursor theme.

## What it does

- Accepts a Windows cursor theme as a directory, `install.inf`, local archive, or direct `http`/`https` URL
- Finds `install.inf`, reads the cursor scheme it defines, and loads the referenced `.ani` and `.cur` files
- Writes a standard Xcursor theme directory with `index.theme` and `cursors/`
- Generates common Xcursor aliases such as `left_ptr`, `hand2`, `xterm`, `watch`, `sb_v_double_arrow`, and `fd_double_arrow`
- Preserves extra Windows roles that do not always exist in Linux themes, including `Pin -> color-picker` and `Person -> person`
- Can copy the generated theme into `~/.local/share/icons` or another install root

## Requirements

- Python `>=3.10`
- Python package `win2xcur>=0.2.0,<0.3`
- ImageMagick available in `PATH`

Optional archive tools:

- No extra tool required for `.zip`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, or `.tar.xz`
- `unrar` or `bsdtar` for `.rar`
- `bsdtar` for `.7z` and `.cab`

## Install

Install from the current checkout:

```bash
pip install .
```

Install in editable mode during development:

```bash
pip install -e .
```

## Platform-Specific Packaging

### Arch Linux

The repo includes a `PKGBUILD` for `win2x11cursor-git`.

```bash
makepkg -si
```

## Usage

`source` can be any of the following:

- A directory containing `install.inf`
- An `install.inf` file
- A local archive
- A direct download URL that resolves to an archive

Show the full CLI help:

```bash
win2x11cursor --help
```

Convert a theme directory into `build/<theme-name>`:

```bash
win2x11cursor MyCursorTheme
```

Convert a local archive:

```bash
win2x11cursor MyCursorTheme.zip
```

Convert a theme from a URL and install it immediately:

```bash
win2x11cursor "https://example.com/MyCursorTheme.zip" --install --force
```

Write generated files under a different output root:

```bash
win2x11cursor MyCursorTheme --output out
```

Override the human-readable source name before the output directory is derived:

```bash
win2x11cursor MyCursorTheme --theme-name "My Cursor Theme"
```

Set the output directory name directly:

```bash
win2x11cursor MyCursorTheme --theme-dir my-cursor-theme
```

Change the inherited Xcursor theme or default size written to `index.theme`:

```bash
win2x11cursor MyCursorTheme --inherits Adwaita --default-size 32
```

Install into a custom icon root instead of `~/.local/share/icons`:

```bash
win2x11cursor MyCursorTheme --install --install-root ~/.icons --force
```

Replace an existing generated output or install target with the same name:

```bash
win2x11cursor MyCursorTheme --force
```

Successful runs print a summary that includes:

- The resolved `install.inf` path
- The generated theme directory name
- The output path
- Converted cursor roles and alias counts
- Any Windows roles that were missing from the source theme
- The install destination when `--install` is used

## Output / Generated Layout

Example output layout:

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

When alias symlinks are supported by the filesystem, the extra cursor names are written as symlinks. Otherwise they are copied as regular files.

## Post-Install Setup

If you used `--install`, the theme is copied to:

```text
~/.local/share/icons/<theme-dir>
```

If you only generated the theme, copy that directory into your icon theme path and select it by directory name.

### X11

Add the theme to `~/.Xresources`:

```text
Xcursor.theme: MyCursorTheme
Xcursor.size: 24
```

Reload X resources or restart the session.

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

- The generated `index.theme` uses the output directory name as `Name`, not the original Windows display name
- The original Windows theme name is kept in the `Comment` field of `index.theme`
- The converter looks for cursor files next to the resolved `install.inf`; if the `.ani` or `.cur` files are elsewhere, conversion fails
- If a directory contains multiple `.inf` files, `win2x11cursor` prefers a single `install.inf`; otherwise it stops with an error instead of guessing
- Archives are validated before extraction and rejected if they contain absolute paths or path traversal entries
- Existing output and install directories are never overwritten unless `--force` is set
- Some desktop environments cache cursors; if a theme change does not appear immediately, log out and back in

## About

`win2x11cursor` is a small Python CLI built on top of `win2xcur`.
