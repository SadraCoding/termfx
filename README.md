# termfx

**Animated terminal headers, ASCII art, system information, and a configurable shell look for Linux.** termfx runs in Bash and Zsh and is designed to work across common Linux distributions. Its animation engine uses Python's standard library; effects do not need downloads, image libraries, or a GPU.

## Highlights

- 76 animated effects plus a random selector, from aurora, fire, matrix rain, and metaballs to mandalas, starfields, waterfalls, and waveforms.
- 66 built-in colour palettes, with automatic effect matching and custom hex colours. The installer lists every effect and every palette (stops, colour preview, hex values) so you can pick by number.
- Animated ASCII art, multi-frame art, built-in examples, and image-to-ASCII helpers when optional image tools are installed.
- System-information panels, Fastfetch presets, Starship themes, prompt styles, profiles, and shell completions.
- Live effect and palette changes, terminal-size handling, pause rules for full-screen programs, and diagnostics.

Run `termfx --help` for the complete command reference and the full effect catalog. Run `termfx effect list` for just the effect names and descriptions.

## Requirements and optional tools

The only runtime requirements are **Bash**, **Python 3**, and standard Unix utilities (`awk`, `sed`, `grep`, `find`, `install`, `tar`, and `gzip`). The installer checks for Python 3 and installs it when system package installation is available. The Python engine imports only modules shipped with Python; there are no Python packages to download.

The installer also attempts to install these companion tools. They improve the shell experience but are optional; termfx continues to run if any are unavailable:

| Tool | Used for | If unavailable |
|---|---|---|
| Fastfetch | System-information display and distro logos | Built-in information panel is used; distro-logo lookup is unavailable |
| Starship | Configurable prompt | Existing shell prompt remains usable |
| eza | Enhanced directory listings | `ls` remains available |
| bat / batcat | Syntax-coloured file viewing | `cat` remains available |
| fzf | Interactive fuzzy selection | Non-interactive selection remains available |
| Git | fzf user-space fallback and Git prompt details | Those optional integrations are skipped |
| fontconfig and JetBrainsMono Nerd Font v3+ | Font detection and terminal icons | Icons can be disabled; select/install a current Nerd Font in the terminal if desired |
| curl or wget | Downloads for user-space fallbacks and fonts | Package-manager installs can still work; download fallbacks are unavailable |
| chafa, jp2a, figlet, toilet | Optional image and text art conversion | Those conversion commands explain which optional tool is needed |

No effect assets or other runtime dependencies are fetched. Package names differ by distribution; the installer maps common names for apt, DNF/YUM, pacman, zypper, apk, XBPS, Gentoo emerge, and Homebrew. If a companion package is missing from a repository or the CPU architecture is unsupported, the installer tries a user-local download where it has a fallback and reports any unavailable optional tool. It does not claim a failed optional install succeeded. You can inspect the result with `termfx doctor`.

## Install

Download the single-file installer from the project's `dist/termfx-install.sh` release artifact, save it, then run:

```sh
sh termfx-install.sh
```

Save the file before running it; piping the installer directly into a shell is unsupported. The installer detects the available package manager and privilege helper (`sudo` or `doas`), installs Python 3 and optional companion tools, and places termfx under your home directory. It may ask for your system password to install packages. On headless or SSH sessions it skips the optional font by default; use `--font` to request it.

Useful installer options:

```sh
sh termfx-install.sh --help
sh termfx-install.sh -y                         # accept installer prompts
sh termfx-install.sh --keep-old                 # keep existing terminal customizations
sh termfx-install.sh --no-packages              # skip package installation (Python 3 is still required)
sh termfx-install.sh --no-font                  # skip the optional font
sh termfx-install.sh --effect starfield --palette photon
sh termfx-install.sh --shell bash               # install shell integration for Bash
```

The normal install backs up supported shell and terminal customizations before applying its selected setup. Use `termfx restore` to restore the backup. `--keep-old` skips that reset. Review `sh termfx-install.sh --help` for all options. Open a new terminal after installation; the default minimum animation area is 80 columns by 24 rows and can be changed in the config.

## First steps

```sh
termfx --help                 # full command help, including every effect
termfx effect list            # effects and descriptions
termfx effect starfield       # set an effect; changes apply live
termfx effect info starfield  # details about one effect
termfx palette list           # list palettes
termfx preview                # preview the current look
termfx doctor                 # inspect terminal, config, and optional tools
```

The same operations work on the configuration directly, for example `termfx set speed 1.3`, `termfx set fps 24`, or `termfx rotate on 120` to cycle effects every 120 seconds. Use `termfx config` to inspect settings and `termfx status` to see current state.

While a command runs, the header is hidden so the command can use the whole screen and its scrollback (output is never cut off or drawn over). **If the output reaches the bottom of the screen, the header stays hidden until you run `clear` (or press Ctrl-L).** Otherwise it comes back at the next prompt.

Set `pause = never` in the config if you want the header to stay on screen while commands run.

### Art

`termfx art list` shows installed art. Use `termfx art add NAME FILE` to import a text file, `termfx art edit NAME` to edit one, and `termfx art use NAME` to select it. Separate animation frames with a line containing `---FRAME---`. Image conversion (`termfx art image`) needs `chafa` or `jp2a`; large text banners need `figlet` or `toilet`; distro logos use Fastfetch. These are optional tools and are not required for ordinary ASCII art or animation.

### Starship

The installer can set up Starship themes. Examples:

```sh
termfx starship list
termfx starship theme list
termfx starship theme developer-forge
termfx starship set right_prompt true
termfx starship set time_format '%H:%M:%S'
termfx starship module on battery
termfx starship preset cloud
```

Theme and prompt settings are stored in termfx-managed config files. `--starship-theme NAME` selects a theme during installation. Starship is optional; the rest of termfx works without it.

## Restore and uninstall

```sh
termfx restore             # restore the backed-up terminal setup
termfx uninstall           # remove termfx and shell hooks
termfx uninstall --purge   # also remove termfx config and imported art
```

Uninstall leaves system packages in place because they may be used by other programs. Remove optional tools with your distribution's package manager if you no longer need them.

## Development

```text
install.sh                 source-tree installer
lib/                       installer UI, package detection, setup and restore steps
src/                       shell CLI, engine, default config, art, Bash/Zsh integration
src/termfx_engine/          modular Python engine: effects, colour, layout and rendering
src/termfx.d/               CLI command modules
gen/themes.py               theme file generator
build.sh                    builds the single-file dist/termfx-install.sh artifact
tests/smoke.sh              installer lifecycle smoke test
```

Run `make build` after source changes to regenerate `dist/termfx-install.sh`. The smoke test uses `--no-packages`; it checks installer lifecycle but does not verify downloads or repository package availability on each distribution. For release validation, test package installation separately in clean distro environments with network access.
