# lib/packages.sh - distro detection, package install, user-space fallbacks, font
# =============================================================================
DISTRO_ID=unknown; DISTRO_LIKE=""; DISTRO_NAME="Linux"; PM=""; SUDO=""; NO_PRIV=0

detect_system() {
  if [[ -r /etc/os-release ]]; then
    eval "$(. /etc/os-release; printf 'DISTRO_ID=%q DISTRO_LIKE=%q DISTRO_NAME=%q' "${ID:-unknown}" "${ID_LIKE:-}" "${PRETTY_NAME:-Linux}")"
  fi
  for pm in pacman apt-get dnf yum zypper apk xbps-install emerge brew; do
    if have "$pm"; then PM=${pm%-get}; PM=${PM%-install}; break; fi
  done
  if ((EUID == 0)); then SUDO=""
  elif have sudo; then SUDO="sudo"
  elif have doas; then SUDO="doas"
  else NO_PRIV=1; fi
  if [[ $PM == brew ]]; then SUDO=""; NO_PRIV=0; fi
  return 0
}

pkg_name() { # logical name -> package name for $PM  (empty = not available)
  local l=$1
  case $PM:$l in
    apt:python|dnf:python|yum:python|zypper:python|apk:python|xbps:python) echo python3 ;;
    emerge:python) echo dev-lang/python ;;
    *:python) echo python ;;
    emerge:curl) echo net-misc/curl ;;
    emerge:fastfetch) echo app-misc/fastfetch ;;
    emerge:eza) echo sys-apps/eza ;;
    emerge:bat) echo sys-apps/bat ;;
    emerge:fzf) echo app-shells/fzf ;;
    emerge:fontconfig) echo media-libs/fontconfig ;;
    emerge:git) echo dev-vcs/git ;;
    emerge:unzip) echo app-arch/unzip ;;
    emerge:xz) echo app-arch/xz-utils ;;
    pacman:font) echo ttf-jetbrains-mono-nerd ;;
    apk:font) echo font-jetbrains-mono-nerd ;;
    brew:font) echo "font-jetbrains-mono-nerd-font" ;;
    *:font) echo "" ;;
    *) echo "$l" ;;
  esac
}

pm_refresh() {
  case $PM in
    apt) $SUDO apt-get update -qq || true ;;
    zypper) $SUDO zypper -n refresh >/dev/null 2>&1 || true ;;
    apk) $SUDO apk update >/dev/null 2>&1 || true ;;
    xbps) $SUDO xbps-install -S -y >/dev/null 2>&1 || true ;;
    dnf|yum) true ;;
  esac
}

pm_install() { # one package at a time so a missing one never aborts the rest
  local p=$1
  case $PM in
    pacman) $SUDO pacman -S --needed --noconfirm "$p" ;;
    apt)    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y "$p" ;;
    dnf|yum) $SUDO "$PM" install -y "$p" ;;
    zypper) $SUDO zypper -n install --no-recommends "$p" ;;
    apk)    $SUDO apk add "$p" ;;
    xbps)   $SUDO xbps-install -y "$p" ;;
    emerge) $SUDO emerge --noreplace --quiet "$p" ;;
    brew)   if [[ $p == font-* ]]; then brew install --cask "$p"; else brew install "$p"; fi ;;   # fonts are casks
    *)      return 1 ;;
  esac
}

try_pkg() { # logical-name
  local p; p=$(pkg_name "$1")
  [[ -n $p ]] || return 1
  info "installing ${CB}$p${C0} via $PM"
  if pm_install "$p" >/dev/null 2>&1; then ok "$p"; return 0; fi
  warn "$p is not available via $PM"; return 1
}

fetch() { # url dest
  local url=$1 out=$2
  if have curl; then curl -fsSL --retry 3 --connect-timeout 15 -o "$out" "$url"
  elif have wget; then wget -q -O "$out" "$url"
  elif have python3; then python3 -c 'import sys,urllib.request as u; u.urlretrieve(sys.argv[1], sys.argv[2])' "$url" "$out"
  else return 1; fi
}

gh_arch() { # echoes tag per tool
  local m; m=$(uname -m)
  case $1:$m in
    fastfetch:x86_64) echo amd64 ;;
    fastfetch:aarch64|fastfetch:arm64) echo aarch64 ;;
    fastfetch:armv7l) echo armv7l ;;
    fastfetch:riscv64) echo riscv64 ;;
    fastfetch:ppc64le) echo ppc64le ;;
    eza:x86_64)
      if have ldd && ldd --version 2>&1 | grep -qi musl; then echo x86_64-unknown-linux-musl
      else echo x86_64-unknown-linux-gnu; fi ;;
    eza:aarch64|eza:arm64)
      if have ldd && ldd --version 2>&1 | grep -qi musl; then echo aarch64-unknown-linux-musl
      else echo aarch64-unknown-linux-gnu; fi ;;
    eza:armv7l) echo arm-unknown-linux-gnueabihf ;;
    *) echo "" ;;
  esac
}

fallback_fastfetch() {
  local a; a=$(gh_arch fastfetch); [[ -n $a ]] || return 1
  local tmp; tmp=$(mktemp -d)
  fetch "https://github.com/fastfetch-cli/fastfetch/releases/latest/download/fastfetch-linux-$a.tar.gz" "$tmp/f.tgz" \
    && tar -xzf "$tmp/f.tgz" -C "$tmp" || { rm -rf "$tmp"; return 1; }
  local b; b=$(find "$tmp" -type f -name fastfetch | head -n1)
  [[ -n $b ]] && install -m755 "$b" "$BIN_DIR/fastfetch"
  rm -rf "$tmp"; [[ -x $BIN_DIR/fastfetch ]]
}
fallback_starship() {
  local tmp; tmp=$(mktemp)
  fetch "https://starship.rs/install.sh" "$tmp" && sh "$tmp" -y -b "$BIN_DIR" >/dev/null 2>&1
  local rc=$?; rm -f "$tmp"; return $rc
}
fallback_eza() {
  local a; a=$(gh_arch eza); [[ -n $a ]] || return 1
  local tmp; tmp=$(mktemp -d)
  fetch "https://github.com/eza-community/eza/releases/latest/download/eza_$a.tar.gz" "$tmp/e.tgz" \
    && tar -xzf "$tmp/e.tgz" -C "$tmp" || { rm -rf "$tmp"; return 1; }
  local b; b=$(find "$tmp" -type f -name eza | head -n1)
  [[ -n $b ]] && install -m755 "$b" "$BIN_DIR/eza"
  rm -rf "$tmp"; [[ -x $BIN_DIR/eza ]]
}
fallback_fzf() {
  have git || return 1
  [[ -d $HOME/.fzf ]] || git clone -q --depth 1 https://github.com/junegunn/fzf.git "$HOME/.fzf" || return 1
  "$HOME/.fzf/install" --bin >/dev/null 2>&1 || return 1
  ln -sf "$HOME/.fzf/bin/fzf" "$BIN_DIR/fzf"
}

ensure_tool() { # command logical [fallback-fn]
  local cmd=$1 logical=$2 fb=${3:-}
  have "$cmd" && { ok "$cmd already installed"; return 0; }
  [[ -x $BIN_DIR/$cmd ]] && { ok "$cmd (user install)"; return 0; }
  if [[ -n $PM && $NO_PRIV == 0 ]]; then try_pkg "$logical" && have "$cmd" && return 0; fi
  if [[ -n $fb ]]; then
    info "trying user-space install of $cmd"
    if "$fb"; then ok "$cmd installed to $BIN_DIR"; return 0; fi
  fi
  warn "$cmd not installed - termfx will fall back gracefully"
  return 1
}

install_packages() {
  detect_system
  info "system: ${CB}$DISTRO_NAME${C0} (id=$DISTRO_ID${DISTRO_LIKE:+, like=$DISTRO_LIKE})  package manager: ${CB}${PM:-none}${C0}"
  [[ $(uname -s) == Linux ]] || warn "non-Linux system detected - best effort only"
  if [[ -n $PM && $NO_PRIV == 1 ]]; then warn "no root/sudo/doas: system packages skipped, using user-space installs"; fi
  if [[ -n $PM && $NO_PRIV == 0 && -n $SUDO ]]; then info "sudo may ask for your password"; $SUDO -v 2>/dev/null || true; fi
  [[ -n $PM && $NO_PRIV == 0 ]] && pm_refresh
  mkdir -p "$BIN_DIR"
  ensure_tool python3 python || die "python3 is required"
  have curl || have wget || ensure_tool curl curl || true
  ensure_tool fastfetch fastfetch fallback_fastfetch || true
  ensure_tool starship starship fallback_starship || true
  ensure_tool eza eza fallback_eza || true
  if ! have bat && ! have batcat; then ensure_tool bat bat || true; fi
  have bat || { have batcat && ln -sf "$(command -v batcat)" "$BIN_DIR/bat"; } || true
  ensure_tool fzf fzf fallback_fzf || true
  have fc-cache || ensure_tool fc-cache fontconfig || true
}

install_font() {
  if have fc-list && fc-list 2>/dev/null | grep -qi "JetBrainsMono.*Nerd\|JetBrainsMonoNL\? Nerd"; then ok "JetBrainsMono Nerd Font already present"; return 0; fi
  if [[ $DO_FONT == auto ]] && { [[ -n ${SSH_CONNECTION:-} ]] || [[ -z ${DISPLAY:-}${WAYLAND_DISPLAY:-} && ${XDG_SESSION_TYPE:-tty} != wayland && ${XDG_SESSION_TYPE:-tty} != x11 ]]; }; then
    info "headless/SSH session: skipping the font (install it on the machine that shows the terminal, or use --font)"; return 0
  fi
  if [[ -n $PM && $NO_PRIV == 0 && -n $(pkg_name font) ]]; then try_pkg font && return 0; fi
  info "downloading JetBrainsMono Nerd Font (user fonts)"
  local tmp; tmp=$(mktemp -d)
  if fetch "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.tar.xz" "$tmp/f.txz"; then
    mkdir -p "$FONT_DIR"
    if ! tar -xJf "$tmp/f.txz" -C "$FONT_DIR" 2>/dev/null; then
      python3 -c 'import sys,tarfile; tarfile.open(sys.argv[1]).extractall(sys.argv[2])' "$tmp/f.txz" "$FONT_DIR" 2>/dev/null || { warn "could not unpack the font"; rm -rf "$tmp"; return 1; }
    fi
    find "$FONT_DIR" -type f ! -iname '*.ttf' ! -iname '*.otf' -delete 2>/dev/null || true
    have fc-cache && fc-cache -f "$FONT_DIR" >/dev/null 2>&1 || true
    ok "font installed to $FONT_DIR - select 'JetBrainsMono Nerd Font' in your terminal if it isn't automatic"
  else warn "font download failed (offline?) - get it from nerdfonts.com"; fi
  rm -rf "$tmp"
}


# tools every later step relies on (git is needed by the fzf fallback, xz/tar by fonts)
ensure_basics() {
  [[ -n $PM && $NO_PRIV == 0 ]] || return 0
  local t pkg
  for t in curl git tar xz unzip fc-cache; do
    have "$t" && continue
    case $t in
      fc-cache) pkg=fontconfig ;;
      xz) if [[ $PM == apt ]]; then pkg=xz-utils; else pkg=xz; fi ;;
      *) pkg=$t ;;
    esac
    try_pkg "$pkg" || warn "could not install $pkg (some optional features may be skipped)"
  done
  return 0
}
