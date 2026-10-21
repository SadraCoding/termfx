# lib/font.sh - make the Nerd Font actually active (otherwise beginners see boxes)
activate_font() {
  local name="JetBrainsMono Nerd Font" did=0 u gpath d
  # never point the terminal at a font that is not installed (e.g. --no-font / --no-packages):
  # the user would get a fallback font and broken icons
  if have fc-list && ! fc-list 2>/dev/null | grep -qi "JetBrainsMono.*Nerd"; then
    warn "$name is not installed - leaving the terminal font alone"
    info "install it (nerdfonts.com), pick it in your terminal, then run: termfx set icons true"
    info "until then a plain prompt (no icons, still with folder + clock) is used"
    "$BIN_DIR/termfx" set icons false >/dev/null 2>&1 || true
    return 0
  fi
  if have gsettings && have gnome-terminal; then
    u=$(gsettings get org.gnome.Terminal.ProfilesList default 2>/dev/null | tr -d "'") || u=""
    [[ -n $u ]] || u="b1dcc9dd-5262-4d8d-a863-c897e6d979b9"
    gpath="org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:$u/"
    if gsettings set "$gpath" use-system-font false 2>/dev/null && gsettings set "$gpath" font "$name 12" 2>/dev/null; then did=1; fi
  fi
  if have konsole; then
    d="$HOME/.local/share/konsole"; mkdir -p "$d"
    printf '[Appearance]\nFont=%s,12,-1,5,50,0,0,0,0,0\n\n[General]\nName=termfx\nParent=FALLBACK/\n' "$name" > "$d/termfx.profile"
    if have kwriteconfig6; then kwriteconfig6 --file konsolerc --group "Desktop Entry" --key DefaultProfile termfx.profile || true
    elif have kwriteconfig5; then kwriteconfig5 --file konsolerc --group "Desktop Entry" --key DefaultProfile termfx.profile || true; fi
    did=1
  fi
  if ((did)); then
    ok "terminal font set to $name"
  else
    warn "could not set the font automatically for your terminal"
    info "open your terminal's Preferences and choose '$name', then run: termfx set icons true"
    info "until then a plain prompt (no icons, still with folder + clock) is used"
    "$BIN_DIR/termfx" set icons false >/dev/null 2>&1 || true
  fi
}
