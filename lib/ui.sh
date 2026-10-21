# lib/ui.sh - colors, logging helpers, banner (sourced by install.sh)
# ------------------------------------------------------------------ ui helpers
if [[ -t 1 && -z ${NO_COLOR:-} ]]; then
  C0=$'\e[0m'; CB=$'\e[1m'; CD=$'\e[2m'
  CR=$'\e[38;5;204m'; CG=$'\e[38;5;114m'; CY=$'\e[38;5;221m'; CC=$'\e[38;5;117m'; CM=$'\e[38;5;183m'
else
  C0=""; CB=""; CD=""; CR=""; CG=""; CY=""; CC=""; CM=""
fi
STEP_N=0; STEP_T=9
step() { STEP_N=$((STEP_N + 1)); printf '\n%s[%d/%d]%s %s%s%s\n' "$CM" "$STEP_N" "$STEP_T" "$C0" "$CB" "$*" "$C0"; }
info() { printf '  %s•%s %s\n' "$CC" "$C0" "$*"; }
ok()   { printf '  %s✔%s %s\n' "$CG" "$C0" "$*"; }
warn() { printf '  %s!%s %s\n' "$CY" "$C0" "$*" >&2; }
err()  { printf '  %s✘%s %s\n' "$CR" "$C0" "$*" >&2; }
die()  { err "$*"; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }
have_tty() { { : </dev/tty; } 2>/dev/null; }

banner() {
  printf '%s' "$CM"
  cat <<'EOF'
  ╔╦╗╔═╗╦═╗╔╦╗╔═╗═╗ ╦
   ║ ║╣ ╠╦╝║║║╠╣ ╔╩╦╝
   ╩ ╚═╝╩╚═╩ ╩╚  ╩ ╚═
EOF
  printf '%s  animated terminal header + pro shell UI  v%s%s\n' "$CD" "$VERSION" "$C0"
}

usage() {
  cat <<EOF
termfx installer v$VERSION

USAGE
  $0 [install|uninstall|restore|doctor] [options]

OPTIONS
  -y, --yes             non-interactive (accept defaults)
  --art FILE            use FILE as your ASCII art (any size, multi-frame ok)
  --art-url URL         download ASCII art from URL
  --art-name NAME       name for the imported art (default: custom)
  --paste               paste ASCII art interactively (finish with Ctrl-D)
  --effect NAME         any effect (termfx effect list) — 57 effects: aurora fire spiral vortex dna tunnel … random
  --palette NAME        palette name or "#hex,#hex,..." (66 palettes; default: auto)
  --fetch-preset NAME   fastfetch panel preset (classic compact minimal clean full gamer server developer aesthetic hybridfetch ultra; default: classic)
  --starship-theme NAME choose a named Starship theme (termfx starship theme list)
  --shell zsh|bash|both|auto   which shell(s) to integrate (default: auto)
  --no-packages         do not install anything (no sudo, no downloads)
  --no-font             skip the Nerd Font
  --font                force font install even with --no-packages
  --no-terminal         do not touch Ghostty / kitty config
  --keep-old            do NOT reset my old terminal customizations (default: back them
                        up to ~/.termfx-backup and start from clean defaults)
  --reset               force a fresh backup even if termfx is already installed
  --keep-fetch          do not disable existing fastfetch/neofetch lines in rc
  --force               overwrite built-in art / config with fresh defaults
  --purge               (uninstall) also delete your config and art
  -h, --help            this help

AFTER INSTALL
  termfx --help         customise art, effects, themes
  termfx doctor         diagnose a missing header / tools
  termfx restore        put your old terminal setup back
EOF
}
