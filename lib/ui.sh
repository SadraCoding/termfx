# shellcheck shell=bash
# lib/ui.sh - colors, logging helpers, banner (sourced by install.sh)
# ------------------------------------------------------------------ ui helpers
if [[ -t 1 && -z ${NO_COLOR:-} ]]; then
  C0=$'\e[0m'; CB=$'\e[1m'; CD=$'\e[2m'
  CR=$'\e[38;5;204m'; CG=$'\e[38;5;114m'; CY=$'\e[38;5;221m'; CC=$'\e[38;5;117m'; CM=$'\e[38;5;183m'
else
  C0=""; CB=""; CD=""; CR=""; CG=""; CY=""; CC=""; CM=""
fi
STEP_N=0; STEP_T=9
# ---- layout helpers -------------------------------------------------------
_tw() { local c=${COLUMNS:-0}; ((c > 0)) || c=$(tput cols 2>/dev/null || echo 80); [[ $c =~ ^[0-9]+$ ]] || c=80; ((c >= 40)) || c=40; printf '%s' "$c"; }
_cw() { local c; c=$(_tw); ((c > 76)) && c=76; printf '%s' "$c"; }   # content width (capped so lines stay readable)
_rule() { local n=$1 s=""; while ((n-- > 0)); do s+="─"; done; printf '%s' "$s"; }
_bar() { local n=$1 t=$2 i s=""; for ((i = 1; i <= t; i++)); do if ((i <= n)); then s+="▰"; else s+="▱"; fi; done; printf '%s' "$s"; }

# step TITLE  - a clear header with a progress bar:   ▰▰▰▱▱▱▱▱▱  3/9  Nerd Font
step() {
  STEP_N=$((STEP_N + 1))
  printf '\n\n  %s%s%s  %s%d/%d%s  %s%s%s\n  %s%s%s\n' \
    "$CM" "$(_bar "$STEP_N" "$STEP_T")" "$C0" "$CD" "$STEP_N" "$STEP_T" "$C0" "$CB" "$*" "$C0" \
    "$CD" "$(_rule $(( $(_cw) - 4 )))" "$C0"
}

# section TITLE  - small caps-style heading inside a step or the summary
section() { printf '\n  %s%s%s\n' "$CB$CM" "${*^^}" "$C0"; }

# Long messages wrap at the terminal width; continuation lines are indented under the text.
_msg() { # colour glyph text...
  local col=$1 g=$2; shift 2
  local w; w=$(( $(_cw) - 6 ))
  local first=1 line
  while IFS= read -r line; do
    if ((first)); then printf '  %s%s%s  %s\n' "$col" "$g" "$C0" "$line"; first=0
    else printf '     %s\n' "$line"; fi
  done < <(printf '%s\n' "$*" | fold -s -w "$w" 2>/dev/null || printf '%s\n' "$*")
}
info() { _msg "$CC" "›" "$*"; }
ok()   { _msg "$CG" "✔" "$*"; }
warn() { _msg "$CY" "▲" "$*" >&2; }
err()  { _msg "$CR" "✘" "$*" >&2; }
die()  { err "$*"; exit 1; }

# item STATE LABEL [DETAIL]  - one aligned row:   ✔  starship       already installed
#   STATE: ok | info | warn | skip | err
item() {
  local st=$1 label=$2 detail=${3:-} g col
  case $st in
    ok)   g="✔"; col=$CG ;;  warn) g="▲"; col=$CY ;;  err) g="✘"; col=$CR ;;
    skip) g="○"; col=$CD ;;  *)    g="›"; col=$CC ;;
  esac
  local w=$(( $(_cw) - 24 )); ((w >= 16)) || w=16
  local first=1 line
  while IFS= read -r line; do
    if ((first)); then printf '  %s%s%s  %s%-14s%s %s%s%s\n' "$col" "$g" "$C0" "$CB" "$label" "$C0" "$CD" "$line" "$C0"; first=0
    else printf '                     %s%s%s\n' "$CD" "$line" "$C0"; fi
  done < <(printf '%s\n' "${detail:- }" | fold -s -w "$w" 2>/dev/null || printf '%s\n' "$detail")
  return 0
}

# spin LABEL CMD...  - run CMD quietly behind an animated spinner; returns CMD's exit status
spin() {
  local label=$1; shift
  if [[ ! -t 1 ]]; then printf '  …  %s\n' "$label"; ( set +e; "$@" ) >/dev/null 2>&1; return; fi
  local frames=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏) i=0 pid rc=0
  ( set +e; "$@" ) >/dev/null 2>&1 </dev/null &
  pid=$!
  trap 'kill "$pid" 2>/dev/null; printf "\r\033[K\033[?25h"; exit 130' INT
  printf '\033[?25l'
  while kill -0 "$pid" 2>/dev/null; do
    printf '\r  %s%s%s  %s%s%s' "$CM" "${frames[i]}" "$C0" "$CD" "$label" "$C0"
    i=$(( (i + 1) % ${#frames[@]} )); sleep 0.1
  done
  wait "$pid" || rc=$?
  trap - INT
  printf '\r\033[K\033[?25h'
  return "$rc"
}

# roadmap  - the whole plan, once, before anything happens (3 columns)
roadmap() {
  local names=("$@") i n=${#@} cols=3 w
  w=$(( ($(_cw) - 4) / cols ))
  printf '\n  %sWhat will happen%s\n\n' "$CB" "$C0"
  for ((i = 0; i < n; i++)); do
    if ((i % cols == 0)); then printf '  '; fi
    printf '%s%d%s %-*s' "$CM" "$((i + 1))" "$C0" "$((w - 2))" "${names[i]}"
    if (((i + 1) % cols == 0 || i == n - 1)); then printf '\n'; fi
  done
  printf '\n'
}

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
  --effect NAME         choose any effect (see the complete catalog after install or run termfx effect list)
  --palette NAME        choose any palette or use "#hex,#hex,..." (complete catalogue after install)
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
