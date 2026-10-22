#!/bin/sh
# =============================================================================
#  termfx installer - animated terminal header + modern shell UI
#  Beginner-friendly: installs what it needs, backs up and resets old
#  customizations, and can restore them anytime ( termfx restore ).
#
#    sh install.sh            install      sh install.sh uninstall
#    sh install.sh -y         no questions sh install.sh restore
#    sh install.sh --help     all options
#
#  (Save the file first; do not pipe it into sh.)
# =============================================================================
if [ -z "${BASH_VERSION:-}" ]; then
  [ -f "$0" ] || { echo "Please save the installer to a file first, then run: sh install.sh"; exit 1; }
  if ! command -v bash >/dev/null 2>&1; then
    echo "bash not found - installing it first..."
    SU=""
    if [ "$(id -u)" -ne 0 ]; then
      if command -v sudo >/dev/null 2>&1; then SU=sudo
      elif command -v doas >/dev/null 2>&1; then SU=doas
      else echo "Need root. Run as root, or ask your admin to install bash."; exit 1; fi
    fi
    if   command -v apk >/dev/null 2>&1;          then $SU apk add bash
    elif command -v apt-get >/dev/null 2>&1;      then $SU apt-get update -qq; $SU apt-get install -y bash
    elif command -v dnf >/dev/null 2>&1;          then $SU dnf install -y bash
    elif command -v yum >/dev/null 2>&1;          then $SU yum install -y bash
    elif command -v zypper >/dev/null 2>&1;       then $SU zypper -n install bash
    elif command -v pacman >/dev/null 2>&1;       then $SU pacman -S --noconfirm bash
    elif command -v xbps-install >/dev/null 2>&1; then $SU xbps-install -y bash
    fi
  fi
  exec bash "$0" "$@"
fi
set -Eeuo pipefail

VERSION="2.3.0"
BIN_DIR="${HOME}/.local/bin"
CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/termfx"
ART_DIR="$CONF_DIR/art"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/termfx"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/termfx"
FONT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/JetBrainsMonoNerd"
MARK_BEGIN="# >>> termfx >>>"
MARK_END="# <<< termfx <<<"
SELF="${BASH_SOURCE[0]:-$0}"
#@DIST_FLAG
if [[ ${TERMFX_DIST:-0} != 1 ]]; then ROOT="$(cd "$(dirname "$SELF")" && pwd)"; fi
#@EMBED

# emit KEY: print a project file (from the source tree, or embedded in the built single-file installer)
emit() {
  if [[ ${TERMFX_DIST:-0} == 1 ]]; then
    local fn="__emb_${1//[^A-Za-z0-9]/_}"; "$fn"
  else
    cat -- "$ROOT/$1"
  fi
}
put() { # KEY DEST [MODE]
  mkdir -p "$(dirname "$2")"; emit "$1" > "$2"; chmod "${3:-644}" "$2"
}

. "$ROOT/lib/ui.sh"
. "$ROOT/lib/packages.sh"
. "$ROOT/lib/steps.sh"
. "$ROOT/lib/reset.sh"
. "$ROOT/lib/font.sh"

# ------------------------------------------------------------------ arguments
CMD=install; RESET=1; ASSUME_YES=0; DO_PKGS=1; DO_FONT=auto; DO_TERM=1; KEEP_FETCH=0
SHELLS=auto; ART_SRC=""; ART_URL=""; ART_NAME=""; PASTE=0; EFFECT=""; PALETTE=""; FETCH_PRESET=""; STARSHIP_THEME=""
FORCE=0; PURGE=0; RESTORE_SRC=""

while (($#)); do
  case $1 in
    install|uninstall|restore|doctor) CMD=$1 ;;
    -y|--yes)        ASSUME_YES=1 ;;
    --art)           ART_SRC=${2:?--art needs a file}; shift ;;
    --art=*)         ART_SRC=${1#*=} ;;
    --art-url)       ART_URL=${2:?--art-url needs a URL}; shift ;;
    --art-url=*)     ART_URL=${1#*=} ;;
    --art-name)      ART_NAME=${2:?}; shift ;;
    --art-name=*)    ART_NAME=${1#*=} ;;
    --paste)         PASTE=1 ;;
    --effect)        EFFECT=${2:?}; shift ;;
    --effect=*)      EFFECT=${1#*=} ;;
    --palette)       PALETTE=${2:?}; shift ;;
    --palette=*)     PALETTE=${1#*=} ;;
    --fetch-preset)  FETCH_PRESET=${2:?}; shift ;;
    --fetch-preset=*) FETCH_PRESET=${1#*=} ;;
    --starship-theme) STARSHIP_THEME=${2:?--starship-theme needs a name}; shift ;;
    --starship-theme=*) STARSHIP_THEME=${1#*=} ;;
    --shell)         SHELLS=${2:?}; shift ;;
    --shell=*)       SHELLS=${1#*=} ;;
    --no-packages)   DO_PKGS=0 ;;
    --no-font)       DO_FONT=0 ;;
    --font)          DO_FONT=1 ;;
    --no-terminal)   DO_TERM=0 ;;
    --keep-fetch)    KEEP_FETCH=1 ;;
    --keep-old)      RESET=0 ;;
    --reset)         RESET=2 ;;
    --force)         FORCE=1 ;;
    --purge)         PURGE=1 ;;
    -h|--help)       usage; exit 0 ;;
    *) if [[ $CMD == restore && $1 != -* && -z $RESTORE_SRC ]]; then RESTORE_SRC=$1   # termfx restore [DIR]
       else die "unknown option: $1 (try --help)"; fi ;;
  esac
  shift
done
case $SHELLS in auto|zsh|bash|both) ;; *) die "--shell must be auto|zsh|bash|both" ;; esac

# ---------------------------------------------------------------- file writers
ART_NAMES="girl arch tux blocks spinner"
ENGINE_MODULES=(src/termfx_engine/__init__.py src/termfx_engine/__main__.py
                src/termfx_engine/_shared.py src/termfx_engine/_system.py
                src/termfx_engine/_color.py src/termfx_engine/_art.py
                src/termfx_engine/_info.py src/termfx_engine/_layout.py
                src/termfx_engine/_effects.py src/termfx_engine/_render.py
                src/termfx_engine/_menu.py src/termfx_engine/_commands.py)
CLI_MODULES=(src/termfx.d/settings.sh src/termfx.d/art.sh src/termfx.d/status.sh)
write_engine() {
  put src/termfx-engine "$BIN_DIR/termfx-engine" 755
  if [[ ${TERMFX_DIST:-0} == 1 ]]; then
    emit engine_bundle | python3 -c 'import io,sys,zipfile; zipfile.ZipFile(io.BytesIO(sys.stdin.buffer.read())).extractall(sys.argv[1])' "$BIN_DIR/termfx_engine"
  else
    local f; for f in "${ENGINE_MODULES[@]}"; do put "$f" "$BIN_DIR/termfx_engine/${f##*/}"; done
  fi
}
write_cli() {
  put src/termfx "$BIN_DIR/termfx" 755
  local f; for f in "${CLI_MODULES[@]}"; do put "$f" "$BIN_DIR/termfx.d/${f##*/}"; done
  put gen/themes.py "$BIN_DIR/termfx-themes" 755
}
write_init_zsh()  { put src/init.zsh  "$CONF_DIR/init.zsh"; }
write_init_bash() { put src/init.bash "$CONF_DIR/init.bash"; }
write_art() {
  local n f; mkdir -p "$ART_DIR"
  for n in $ART_NAMES; do
    f="$ART_DIR/$n.txt"
    if [[ ! -f $f || $FORCE == 1 ]]; then put "src/art/$n.txt" "$f"; fi
  done
}
write_default_config() {
  [[ -f $CONF_DIR/config && $FORCE != 1 ]] && return 0
  put src/config.default "$CONF_DIR/config"
}
write_generated_configs() {
  have python3 || { warn "python3 missing - skipping starship/fastfetch themes"; return 0; }
  emit gen/themes.py | CONF_DIR="$CONF_DIR" python3 -
}
rc_patch() { # file mode(install|clean|uninstall) init keep_fetch
  emit lib/rcpatch.py | python3 - "$1" "$2" "${3:-}" "${4:-0}"
}

# keep a copy of the installer so  termfx uninstall / termfx restore  work later
keep_installer_copy() {
  mkdir -p "$DATA_DIR"
  if [[ ${TERMFX_DIST:-0} == 1 ]]; then
    if [[ -r $SELF && -f $SELF ]]; then install -m755 "$SELF" "$DATA_DIR/install.sh" 2>/dev/null || true; fi
  else
    rm -rf "$DATA_DIR/tree"; mkdir -p "$DATA_DIR/tree"
    cp -r "$ROOT/install.sh" "$ROOT/lib" "$ROOT/src" "$ROOT/gen" "$DATA_DIR/tree/"
    printf '#!/bin/sh\nexec sh "%s/tree/install.sh" "$@"\n' "$DATA_DIR" > "$DATA_DIR/install.sh"
    chmod 755 "$DATA_DIR/install.sh"
  fi
}

do_install() {
  banner
  [[ $(id -u) -eq 0 && -z ${SUDO_USER:-} && ${TERMFX_ALLOW_ROOT:-0} != 1 ]] && warn "running as root: everything will be installed for root's HOME ($HOME)"
  have python3 || [[ $DO_PKGS == 1 ]] || die "python3 is required (re-run without --no-packages)"

  step "Installing packages (fastfetch, starship, eza, bat, fzf)"
  if ((DO_PKGS)); then install_packages; ensure_basics; else info "skipped (--no-packages)"; detect_system; mkdir -p "$BIN_DIR"; have python3 || die "python3 is required"; fi

  step "Nerd Font"
  if [[ $DO_FONT == 0 ]]; then info "skipped (--no-font)"
  elif [[ $DO_FONT == 1 ]]; then install_font || warn "font setup failed; continuing with icons disabled until a Nerd Font v3+ is selected"
  elif ((DO_PKGS)); then install_font || warn "font setup failed; continuing with icons disabled until a Nerd Font v3+ is selected"
  else info "skipped (--no-packages; pass --font to force)"; fi

  step "Resetting old terminal customizations"
  if ((RESET)); then reset_to_defaults; else info "skipped (--keep-old)"; fi

  step "Writing termfx files"
  mkdir -p "$BIN_DIR" "$CONF_DIR" "$ART_DIR" "$DATA_DIR" "$CACHE_DIR"
  write_engine; write_cli; ok "engine + CLI -> $BIN_DIR"
  write_init_zsh; write_init_bash; ok "shell integrations (zsh, bash)"
  write_art; ok "built-in art -> $ART_DIR"
  write_default_config; write_generated_configs; ok "config, starship + fastfetch themes -> $CONF_DIR"
  keep_installer_copy
  python3 -m compileall -q "$BIN_DIR/termfx_engine" 2>/dev/null && ok "engine compiles" || die "engine failed to compile"
  export PATH="$BIN_DIR:$PATH"

  step "Your ASCII art"
  art_wizard
  starship_theme_wizard
  [[ -n $EFFECT ]] && "$BIN_DIR/termfx" effect "$EFFECT" >/dev/null || true
  [[ -n $PALETTE ]] && "$BIN_DIR/termfx" palette "$PALETTE" >/dev/null || true
  [[ -n $FETCH_PRESET ]] && "$BIN_DIR/termfx" fastfetch "$FETCH_PRESET" >/dev/null || true

  step "Terminal emulator look"
  integrate_terminals

  step "Hooking into your shell(s)"
  choose_shells
  integrate_shells

  step "Pre-computing art cache"
  if [[ -t 1 ]]; then "$BIN_DIR/termfx-engine" prepare 2>/dev/null && ok "cached (large art is scaled once, then loads instantly)" || true
  else info "will be cached on first start"; fi

  activate_font

  step "Done"
  finish_message
}

do_uninstall() {
  banner
  STEP_T=4
  step "Removing shell integration"
  local f res
  for f in "${ZDOTDIR:-$HOME}/.zshrc" "$HOME/.bashrc" "${ZDOTDIR:-$HOME}/.zprofile" "${ZDOTDIR:-$HOME}/.zshenv" "$HOME/.bash_profile" "$HOME/.profile"; do
    [[ -f $f ]] || continue
    res=$(rc_patch "$f" uninstall "" 0); [[ $res == patched ]] && ok "cleaned $f"
  done
  step "Removing terminal includes"
  for f in "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/config" "${XDG_CONFIG_HOME:-$HOME/.config}/kitty/kitty.conf"; do
    [[ -f $f ]] && grep -q termfx "$f" && { sed -i '/^# termfx$/d;/termfx\/\(ghostty\|kitty\)\.conf/d' "$f"; ok "cleaned $f"; }
  done
  step "Removing files"
  pkill -u "$(id -un)" -f 'termfx-engine run' 2>/dev/null || true
  rm -f "$BIN_DIR/termfx" "$BIN_DIR/termfx-engine" "$BIN_DIR/termfx-themes"; rm -rf "$BIN_DIR/termfx.d" "$BIN_DIR/termfx_engine" "$CACHE_DIR"
  rm -f "$CONF_DIR/init.zsh" "$CONF_DIR/init.bash"
  if ((PURGE)); then rm -rf "$CONF_DIR"; ok "config and art deleted"; else info "kept your config/art in $CONF_DIR (use --purge to delete)"; fi
  printf '\x1b[r' 2>/dev/null || true
  if [[ -f $BACKUP_ROOT/original/MANIFEST || -f $BACKUP_ROOT/latest/MANIFEST ]]; then
    local a; a=$(ask "  Restore the terminal setup you had before termfx? [y/N]: " "n")
    [[ $a =~ ^[Yy] ]] && restore_backup
  fi
  rm -rf "$DATA_DIR"
  step "Done"
  ok "termfx removed. Packages (fastfetch, starship, eza...) were left installed. Open a new terminal."
}

case $CMD in
  install)   do_install ;;
  uninstall) do_uninstall ;;
  restore)   restore_backup "${RESTORE_SRC:-}" ;;
  doctor)
    if [[ -x $BIN_DIR/termfx-engine ]]; then exec "$BIN_DIR/termfx-engine" doctor
    else die "termfx is not installed yet. Run the installer first, then: termfx doctor"; fi ;;
esac
