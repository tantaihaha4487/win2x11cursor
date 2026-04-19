# win2x11cursor

Convert Windows cursor themes into installable X11/Xcursor themes.

`win2x11cursor` accepts a Windows cursor theme as a directory, `install.inf`, local archive, or direct archive URL, then writes a standard Xcursor theme directory with `index.theme` and `cursors/`.

## Highlights

- Works with theme folders, `install.inf`, local archives, and direct `http`/`https` archive URLs
- Reads Windows cursor schemes from `install.inf`
- Converts both `.cur` and `.ani` cursors through `win2xcur`
- Writes a normal Xcursor theme layout you can install locally
- Generates common Xcursor aliases like `left_ptr`, `hand2`, `xterm`, and `watch`
- Preserves extra Windows roles such as `Pin -> color-picker` and `Person -> person`
- When an archive contains both `Static/install.inf` and `Windows/install.inf`, it prefers `Windows/install.inf`

## Requirements

- Python `>=3.10`
- `win2xcur>=0.2.0,<0.3`
- ImageMagick in `PATH`

Optional archive tools:

- No extra tool required for `.zip`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, or `.tar.xz`
- `unrar` or `bsdtar` for `.rar`
- `bsdtar` for `.7z` and `.cab`

## Install

### Arch Linux

Install the AUR package `win2x11cursor-git`:

```bash
paru -S win2x11cursor-git
```

Or:

```bash
yay -S win2x11cursor-git
```

Package page:

```text
https://aur.archlinux.org/packages/win2x11cursor-git
```

### From Source

Install from the current checkout:

```bash
pip install .
```

Install in editable mode for development:

```bash
pip install -e .
```

If you want to build the Arch package from this checkout, the repo also includes a `PKGBUILD`:

```bash
makepkg -si
```

## Quick Start

Convert a local archive into `build/<theme-name>`:

```bash
win2x11cursor "/path/to/MyCursorTheme.zip"
```

Convert and install it into `~/.local/share/icons`:

```bash
win2x11cursor "/path/to/MyCursorTheme.zip" --install --force
```

Then select the generated theme in your desktop environment.

Examples:

```bash
gsettings set org.gnome.desktop.interface cursor-theme 'mycursortheme'
plasma-apply-cursortheme mycursortheme
hyprctl setcursor mycursortheme 24
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

Convert a theme directory:

```bash
win2x11cursor MyCursorTheme
```

Convert a local archive:

```bash
win2x11cursor MyCursorTheme.zip
```

Convert a direct archive URL and install it immediately:

```bash
win2x11cursor "https://example.com/MyCursorTheme.zip" --install --force
```

Write generated files under a different output root:

```bash
win2x11cursor MyCursorTheme --output out
```

Override the source theme name before the output directory is derived:

```bash
win2x11cursor MyCursorTheme --theme-name "My Cursor Theme"
```

Set the generated output directory name directly:

```bash
win2x11cursor MyCursorTheme --theme-dir my-cursor-theme
```

Change the inherited Xcursor theme or default size written to `index.theme`:

```bash
win2x11cursor MyCursorTheme --inherits Adwaita --default-size 32
```

Install into a custom icon root:

```bash
win2x11cursor MyCursorTheme --install --install-root ~/.icons --force
```

Replace an existing generated output or install target with the same name:

```bash
win2x11cursor MyCursorTheme --force
```

Successful runs print a summary with:

- The resolved `install.inf` path
- The generated theme directory name
- The output path
- Converted cursor roles and alias counts
- Any Windows roles that were missing from the source theme
- The install destination when `--install` is used

## Output Layout

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

When symlinks are supported, extra cursor names are written as symlinks. Otherwise they are copied as regular files.

## After Install

With `--install`, the theme is copied to:

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

- The generated `index.theme` uses the output directory name as `Name`
- The original Windows theme name is kept in the `Comment` field of `index.theme`
- Cursor files must exist next to the resolved `install.inf`
- If an archive contains multiple `install.inf` files, `win2x11cursor` prefers a `Windows/` variant when present
- Archives are validated before extraction and rejected if they contain absolute paths or path traversal entries
- Existing output and install directories are not overwritten unless `--force` is set
- Some desktop environments cache cursors, so logging out and back in may be required
