# lib/steps.sh - shell/terminal integration, art wizard, finish message
choose_shells() {
  local login="${SHELL##*/}" s
  TARGETS=()
  case $SHELLS in
    zsh) TARGETS=(zsh) ;; bash) TARGETS=(bash) ;; both) TARGETS=(zsh bash) ;;
    auto)
      for s in zsh bash; do
        have "$s" || continue
        local rc="$HOME/.${s}rc"; [[ $s == zsh ]] && rc="${ZDOTDIR:-$HOME}/.zshrc"
        if [[ $login == "$s" || -f $rc ]]; then TARGETS+=("$s"); fi
      done
      ((${#TARGETS[@]})) || TARGETS=(bash) ;;
  esac
}

integrate_shells() {
  local s rc
  for s in "${TARGETS[@]}"; do
    rc="$HOME/.${s}rc"; [[ $s == zsh ]] && rc="${ZDOTDIR:-$HOME}/.zshrc"
    local res; res=$(rc_patch "$rc" install "$CONF_DIR/init.$s" "$KEEP_FETCH")
    ok "$s: $rc ($res; backup kept when changed)"
  done
  if ((! KEEP_FETCH)); then
    local f
    for f in "${ZDOTDIR:-$HOME}/.zprofile" "${ZDOTDIR:-$HOME}/.zshenv" "$HOME/.bash_profile" "$HOME/.profile"; do
      if [[ -f $f ]]; then rc_patch "$f" clean "" 0 >/dev/null; fi
    done
  fi
  return 0
}

integrate_terminals() {
  ((DO_TERM)) || return 0
  local did=0
  if have ghostty || [[ -d ${XDG_CONFIG_HOME:-$HOME/.config}/ghostty ]]; then
    local d="${XDG_CONFIG_HOME:-$HOME/.config}/ghostty" f
    mkdir -p "$d"; f="$d/config"; touch "$f"
    if ! grep -q 'termfx/ghostty.conf' "$f"; then
      cp -n "$f" "$f.termfx.bak" 2>/dev/null || true
      printf '\n# termfx\nconfig-file = ?%s/ghostty.conf\n' "$CONF_DIR" >> "$f"
    fi
    ok "Ghostty: loads $CONF_DIR/ghostty.conf (your own settings stay untouched)"; did=1
  fi
  if have kitty || [[ -d ${XDG_CONFIG_HOME:-$HOME/.config}/kitty ]]; then
    local d="${XDG_CONFIG_HOME:-$HOME/.config}/kitty" f
    mkdir -p "$d"; f="$d/kitty.conf"; touch "$f"
    if ! grep -q 'termfx/kitty.conf' "$f"; then
      cp -n "$f" "$f.termfx.bak" 2>/dev/null || true
      printf '\n# termfx\ninclude %s/kitty.conf\n' "$CONF_DIR" >> "$f"
    fi
    ok "kitty: includes $CONF_DIR/kitty.conf"; did=1
  fi
  ((did)) || info "no Ghostty/kitty found - for other terminals just pick the 'JetBrainsMono Nerd Font' font (theme snippets are in $CONF_DIR)"
}

ask() { # prompt default
  local a=""
  if ((ASSUME_YES)) || ! have_tty; then printf '%s' "$2"; return; fi
  read -r -p "$1" a </dev/tty || a=""
  printf '%s' "${a:-$2}"
}

art_wizard() {
  local termfx="$BIN_DIR/termfx"
  # explicit flags first
  if [[ -n $ART_SRC ]]; then
    [[ -f $ART_SRC ]] || die "art file not found: $ART_SRC"
    "$termfx" art add "${ART_NAME:-custom}" "$ART_SRC" -u || warn "could not import art"; return 0
  fi
  if [[ -n $ART_URL ]]; then "$termfx" art add "${ART_NAME:-custom}" "$ART_URL" -u || warn "could not download art"; return 0; fi
  if ((PASTE)); then
    have_tty || die "--paste needs a terminal"
    printf '%sPaste your ASCII art, then press Ctrl-D on an empty line:%s\n' "$CB" "$C0"
    "$termfx" art add "${ART_NAME:-custom}" - -u </dev/tty || true; return 0
  fi
  ((ASSUME_YES)) && return 0
  have_tty || return 0

  local names=() n i=0
  while IFS= read -r n; do names+=("$n"); done < <("$BIN_DIR/termfx-engine" list art)
  printf '\n  %sChoose your header art:%s\n' "$CB" "$C0"
  for n in "${names[@]}"; do i=$((i+1)); printf '   %s%2d)%s %s\n' "$CM" "$i" "$C0" "$n"; done
  printf '   %s p)%s paste my own ASCII art now\n   %s f)%s load from a file / URL\n   %s d)%s my distro logo (needs fastfetch)\n   %s r)%s random each time\n' "$CM" "$C0" "$CM" "$C0" "$CM" "$C0" "$CM" "$C0"
  local c; c=$(ask "  choice [1]: " "1")
  case $c in
    p|P) printf '  %sPaste now, finish with Ctrl-D on an empty line:%s\n' "$CD" "$C0"
         "$termfx" art add custom - -u </dev/tty || true ;;
    f|F) local s; s=$(ask "  path or URL: " "")
         if [[ -z $s ]]; then warn "no path given - keeping default art"
         else "$termfx" art add custom "$s" -u || warn "import failed"; fi ;;
    d|D) "$termfx" art distro || warn "could not get distro logo (is fastfetch installed?)" ;;
    r|R) "$termfx" set art random >/dev/null; ok "art = random (picks a new one each terminal)" ;;
    ''|*[!0-9]*)
      if [[ -n $c && $c != 1 ]]; then warn "invalid choice '$c' - using #1 (${names[0]:-girl})"; fi
      [[ ${#names[@]} -ge 1 ]] && { "$termfx" set art "${names[0]}" >/dev/null; ok "art = ${names[0]}"; } ;;
    *) if ((c >= 1 && c <= ${#names[@]})); then
         "$termfx" set art "${names[c-1]}" >/dev/null; ok "art = ${names[c-1]}"
       else
         warn "choice out of range - using #1 (${names[0]:-girl})"
         [[ ${#names[@]} -ge 1 ]] && { "$termfx" set art "${names[0]}" >/dev/null; ok "art = ${names[0]}"; }
       fi ;;
  esac

  if [[ -z $EFFECT ]]; then
    local fx=()
    local descs=()
    while IFS= read -r n; do
      fx+=("${n%% *}")
      descs+=("${n#"${n%% *}"}"); descs[-1]=${descs[-1]## }
    done < <("$BIN_DIR/termfx-engine" list effects)
    ((${#fx[@]})) || fx=(aurora wave rainbow plasma fire matrix pulse static)
    printf '\n  %s%s effects available%s (enter a number, type a name, or press Enter for aurora):\n' "$CB" "${#fx[@]}" "$C0"
    local i
    for i in "${!fx[@]}"; do
      printf '   %s%2d)%s %-13s %s%s%s\n' "$CM" "$((i+1))" "$C0" "${fx[i]}" "$CD" "${descs[i]}" "$C0"
    done
    c=$(ask "  effect [1=aurora]: " "1")
    if [[ $c =~ ^[0-9]+$ ]] && ((c >= 1 && c <= ${#fx[@]})); then
      EFFECT=${fx[c-1]}; ok "effect = $EFFECT"
    elif [[ -n $c && $c != 1 ]]; then
      local found=0
      for n in "${fx[@]}"; do [[ $n == "$c" ]] && { EFFECT=$c; found=1; break; }; done
      if ((found)); then ok "effect = $EFFECT"
      else warn "unknown effect '$c' - using aurora"; EFFECT=aurora; fi
    else
      EFFECT=aurora
    fi
  fi

  # palette selection
  if [[ -z $PALETTE ]]; then
    local pals=()
    while IFS= read -r n; do pals+=("$n"); done < <("$BIN_DIR/termfx-engine" list palettes)
    if ((${#pals[@]})); then
      printf '\n  %s%s palettes%s (or press Enter for auto = best per effect):\n' "$CB" "${#pals[@]}" "$C0"
      local p i=0
      # show first 20 + auto option
      for p in "${pals[@]:0:20}"; do
        i=$((i+1)); printf '   %s%2d)%s %s\n' "$CM" "$i" "$C0" "$p"
      done
      printf '   %s  …%s (%d more: termfx palette list)\n' "$CD" "$C0" "${#pals[@]}"
      printf '   %s a)%s auto (recommended - matches the effect)\n' "$CM" "$C0"
      c=$(ask "  palette [a=auto]: " "a")
      if [[ $c == a || $c == A || -z $c ]]; then
        PALETTE=auto
      elif [[ $c =~ ^[0-9]+$ ]] && ((c >= 1 && c <= ${#pals[@]})); then
        PALETTE=${pals[c-1]}
      else
        local pfound=0
        for p in "${pals[@]}"; do [[ $p == "$c" ]] && { PALETTE=$c; pfound=1; break; }; done
        ((pfound)) || PALETTE=auto
      fi
      ok "palette = $PALETTE"
    fi
  fi

  # fastfetch panel preset
  if [[ -z ${FETCH_PRESET:-} ]]; then
    local fpresets=() fpdescs=()
    while IFS= read -r line; do
      fpresets+=("${line%% *}")
      fpdescs+=("${line#* }")
    done < <(CONF_DIR="$CONF_DIR" python3 "$BIN_DIR/termfx-themes" --list fetch 2>/dev/null)
    if ((${#fpresets[@]})); then
      printf '\n  %s%s Fastfetch panel presets%s (Enter = classic):\n' "$CB" "${#fpresets[@]}" "$C0"
      local fi2
      for fi2 in "${!fpresets[@]}"; do
        printf '   %s%2d)%s %-13s %s%s%s\n' "$CM" "$((fi2+1))" "$C0" "${fpresets[$fi2]}" "$CD" "${fpdescs[$fi2]}" "$C0"
      done
      c=$(ask "  fetch preset [1=classic]: " "1")
      if [[ $c =~ ^[0-9]+$ ]] && ((c >= 1 && c <= ${#fpresets[@]})); then
        FETCH_PRESET=${fpresets[c-1]}
      elif [[ -n $c && $c != 1 ]]; then
        local ffound=0
        for n in "${fpresets[@]}"; do [[ $n == "$c" ]] && { FETCH_PRESET=$c; ffound=1; break; }; done
        ((ffound)) || FETCH_PRESET=classic
      else
        FETCH_PRESET=classic
      fi
      ok "fetch preset = $FETCH_PRESET"
    fi
  fi
}

starship_theme_wizard() {
  local current choice
  if [[ -n ${STARSHIP_THEME:-} ]]; then
    "$BIN_DIR/termfx" starship theme "$STARSHIP_THEME"
    return
  fi
  ((ASSUME_YES)) && return 0
  have_tty || return 0
  current=$(awk -F= '/^[[:space:]]*starship_theme[[:space:]]*=/ {split($2, v, "#"); gsub(/[[:space:]]/, "", v[1]); print v[1]}' "$CONF_DIR/config" 2>/dev/null | tail -n1)
  current=${current:-terminal-match}
  printf '\n  %sStarship prompt themes%s (files are saved under %s/starship-themes/):\n' "$CB" "$C0" "$CONF_DIR"
  CONF_DIR="$CONF_DIR" python3 "$BIN_DIR/termfx-themes" --list starship | sed 's/^/    /'
  choice=$(ask "  theme [Enter keeps $current]: " "")
  [[ -z $choice ]] && { info "keeping Starship theme: $current"; return 0; }
  "$BIN_DIR/termfx" starship theme "$choice"
}

_tool_line() { # cmd label
  if have "$1"; then printf '    %s✔%s %-12s ready\n' "$CG" "$C0" "$2"
  else printf '    %s·%s %-12s not installed (optional)\n' "$CD" "$C0" "$2"; fi
}

finish_message() {
  cat <<EOF

${CG}${CB}  ✔ termfx $VERSION installed${C0}

  ${CB}Open a new terminal${C0} (or run ${CC}exec \$SHELL${C0}) to see the animated header.
  Needs about ${CB}80×24${C0} or larger - below that the header hides itself (prompt still works).
  If p10k or oh-my-posh remains active (--keep-old), keep only one prompt framework enabled.

  ${CB}What's ready${C0}
EOF
  _tool_line python3   python3
  _tool_line starship  starship
  _tool_line fastfetch fastfetch
  _tool_line eza       eza
  { have bat || have batcat; } && printf '    %s✔%s %-12s ready\n' "$CG" "$C0" "bat" \
    || printf '    %s·%s %-12s not installed (optional)\n' "$CD" "$C0" "bat"
  _tool_line fzf       fzf
  cat <<EOF

  ${CB}Features & commands${C0}
    ${CC}termfx effect list${C0}                 57 animated effects (aurora fire matrix dna tunnel …)
    ${CC}termfx effect next${C0}               cycle through effects live
    ${CC}termfx effect info NAME${C0}          details + recommended palette
    ${CC}termfx palette list${C0}              66 colour palettes
    ${CC}termfx palette show NAME${C0}         preview colours with gradient
    ${CC}termfx palette next${C0}              cycle through palettes
    ${CC}termfx preview effect=fire${C0}       full-screen preview (any key to exit)
    ${CC}termfx theme list${C0}                 change shell/prompt colours
    ${CC}termfx starship theme list${C0}        browse named prompt themes
    ${CC}termfx starship theme cloud-ops${C0}    apply a Starship theme
    ${CC}termfx art add mine${C0}               paste your own ASCII (any size)
    ${CC}termfx info items${C0}                 manage the system info panel
    ${CC}termfx info custom \"CMD\"${C0}          custom info panel command
    ${CC}termfx randomize${C0}                  instant random look
    ${CC}termfx profile save work${C0}         save/load config profiles
    ${CC}termfx --help${C0}                     full feature list

  ${CB}Quick tips${C0}
    ${CC}termfx starship theme developer-forge${C0} named Starship theme (14 choices: termfx starship theme list)
    ${CC}termfx starship set right_prompt true${C0} customize Starship controls
    ${CC}termfx fastfetch gamer${C0}             switch info panel preset (11 styles: termfx fastfetch list)
    ${CC}termfx glitch on${C0}                   enable random glitch distortions
    ${CC}termfx info-colors neon${C0}            colour the info panel with any palette
    ${CC}termfx set sparkle true${C0}           add sparkle effect to the header
    ${CC}termfx set vignette true${C0}         cinematic edge darkening
    ${CC}termfx rotate on 60${C0}              auto-rotate effects every 60s
    ${CC}termfx align center${C0}              centre the header

  Restore old setup:  ${CC}termfx restore${C0}
  Uninstall:          ${CC}termfx uninstall${C0}
  Something wrong?:   ${CC}termfx doctor${C0}
EOF
  case ":$PATH:" in *":$BIN_DIR:"*) ;; *) warn "$BIN_DIR is not in your PATH yet - it will be after you open a new terminal." ;; esac
}
