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
  for n in "${names[@]}"; do i=$((i+1)); printf '   %s%3d)%s %s\n' "$CM" "$i" "$C0" "$n"; done
  printf '   %s  p)%s paste my own ASCII art now\n   %s  f)%s load from a file / URL\n   %s  d)%s my distro logo (needs fastfetch)\n   %s  r)%s random each time\n' "$CM" "$C0" "$CM" "$C0" "$CM" "$C0" "$CM" "$C0"
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
    local fx=() descs=() fxpal=() line
    while IFS=$'\t' read -r n line c; do
      fx+=("$n"); descs+=("$line"); fxpal+=("$c")
    done < <("$BIN_DIR/termfx-engine" list effect-menu)
    ((${#fx[@]})) || fx=(aurora wave rainbow plasma fire matrix pulse static)
    printf '\n  %s%s effects%s - pick a number or a name (Enter = aurora):\n' "$CB" "${#fx[@]}" "$C0"
    local i ecols; ecols=$(_tw)
    for i in "${!fx[@]}"; do
      if ((ecols >= 80)); then
        printf '   %s%3d)%s %-14s %s%-36s palette: %s%s\n' "$CM" "$((i+1))" "$C0" "${fx[i]}" "$CD" "${descs[i]:-}" "${fxpal[i]:-auto}" "$C0"
      else       # narrow terminal: keep each entry on one line so nothing wraps into the next row
        printf '   %s%3d)%s %-14s %s%.*s%s\n' "$CM" "$((i+1))" "$C0" "${fx[i]}" "$CD" "$((ecols > 26 ? ecols - 26 : 0))" "${descs[i]:-}" "$C0"
      fi
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
    local pals=() pstops=() phex=() n2
    while IFS= read -r n; do
      pals+=("${n%% *}")
      n2=${n#* }; pstops+=("${n2%% *}"); phex+=("${n2#* }")
    done < <("$BIN_DIR/termfx-engine" list palette-menu)
    if ((${#pals[@]})); then
      local pcols=${COLUMNS:-0}
      ((pcols > 0)) || pcols=$(tput cols 2>/dev/null || echo 80)
      printf '\n  %s%s palettes%s - pick a number or a name (Enter = auto = best for the effect):\n' "$CB" "${#pals[@]}" "$C0"
      local p i h r g bl sw hx
      for i in "${!pals[@]}"; do
        sw=""; hx=""
        for h in ${phex[i]}; do
          hx+="#$h "
          if [[ -n $C0 ]]; then
            r=$((16#${h:0:2})); g=$((16#${h:2:2})); bl=$((16#${h:4:2}))
            sw+=$(printf '\033[48;2;%d;%d;%dm  ' "$r" "$g" "$bl")      # colour swatch; the hex text keeps the normal colour so it stays readable on any background
          fi
        done
        [[ -n $sw ]] && sw+=$C0
        hx=${hx% }
        if ((pcols >= 112)); then      # wide terminal: everything on one line
          printf '   %s%3d)%s %-14s %s%d stops%s  %s%*s %s%s%s\n' "$CM" "$((i+1))" "$C0" "${pals[i]}" "$CD" "${pstops[i]}" "$C0" "$sw" "$(( (8 - ${pstops[i]}) * 2 ))" "" "$CD" "$hx" "$C0"
        else                           # narrow terminal: hex values on their own line so nothing wraps
          printf '   %s%3d)%s %-14s %s%d stops%s  %s\n' "$CM" "$((i+1))" "$C0" "${pals[i]}" "$CD" "${pstops[i]}" "$C0" "$sw"
          printf '%s\n' "$hx" | fold -s -w "$((pcols > 16 ? pcols - 8 : 8))" | while IFS= read -r hl; do printf '        %s%s%s\n' "$CD" "${hl%"${hl##*[![:space:]]}"}" "$C0"; done
        fi
      done
      printf '   %s  a)%s %-14s %sbest palette for the chosen effect (recommended)%s\n' "$CM" "$C0" "auto" "$CD" "$C0"
      c=$(ask "  palette (number, name, or custom #hex,#hex,...) [a=auto]: " "a")
      if [[ $c == a || $c == A || -z $c ]]; then
        PALETTE=auto
      elif [[ $c =~ ^[0-9]+$ ]] && ((c >= 1 && c <= ${#pals[@]})); then
        PALETTE=${pals[c-1]}
      elif [[ $c =~ ^#?[0-9a-fA-F]{6}(,#?[0-9a-fA-F]{6})+$ ]]; then
        PALETTE=$c                                  # custom colours, e.g. #ff0080,#00e5ff,#7a00ff
      else
        local pfound=0
        for p in "${pals[@]}"; do [[ $p == "$c" ]] && { PALETTE=$c; pfound=1; break; }; done
        if ((!pfound)); then warn "unknown palette '$c' - using auto"; PALETTE=auto; fi
      fi
      ok "palette = $PALETTE"
    fi
  fi

  # fastfetch panel preset
  if [[ -z ${FETCH_PRESET:-} ]]; then
    local fpresets=() fpdescs=()
    while IFS= read -r line; do
      fpresets+=("${line%% *}")
      fpdescs+=("$(printf '%s' "${line#* }" | sed 's/^[[:space:]]*//')")
    done < <(CONF_DIR="$CONF_DIR" python3 "$BIN_DIR/termfx-themes" --list fetch 2>/dev/null)
    if ((${#fpresets[@]})); then
      printf '\n  %s%s Fastfetch panel presets%s (Enter = classic):\n' "$CB" "${#fpresets[@]}" "$C0"
      local fi2
      for fi2 in "${!fpresets[@]}"; do
        printf '   %s%3d)%s %-14s %s%s%s\n' "$CM" "$((fi2+1))" "$C0" "${fpresets[$fi2]}" "$CD" "${fpdescs[$fi2]}" "$C0"
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
  local snames=() sdescs=() n d i
  while IFS= read -r n; do
    snames+=("${n%% *}"); d=${n#* }; sdescs+=("${d#"${d%%[![:space:]]*}"}")
  done < <(CONF_DIR="$CONF_DIR" python3 "$BIN_DIR/termfx-themes" --list starship)
  printf '\n  %s%s Starship prompt themes%s - pick a number or a name:\n' "$CB" "${#snames[@]}" "$C0"
  for i in "${!snames[@]}"; do
    printf '   %s%3d)%s %-20s %s%s%s%s\n' "$CM" "$((i+1))" "$C0" "${snames[i]}" "$CD" "${sdescs[i]}" "$C0" "$([[ ${snames[i]} == "$current" ]] && printf ' (current)')"
  done
  choice=$(ask "  theme [Enter keeps $current]: " "")
  [[ -z $choice ]] && { info "keeping Starship theme: $current"; return 0; }
  if [[ $choice =~ ^[0-9]+$ ]]; then
    if ((choice >= 1 && choice <= ${#snames[@]})); then choice=${snames[choice-1]}
    else warn "choice out of range - keeping $current"; return 0; fi
  fi
  "$BIN_DIR/termfx" starship theme "$choice"
}

_tool_line() { # cmd label
  if have "$1"; then printf '    %s✔%s %-12s ready\n' "$CG" "$C0" "$2"
  else printf '    %s·%s %-12s not installed (optional)\n' "$CD" "$C0" "$2"; fi
}

# one aligned line of the summary: command (coloured) + padded description column
_cmd() { printf '    %s%-40s%s %s\n' "$CC" "$1" "$C0" "$2"; }

finish_message() {
  cat <<EOF

${CG}${CB}  ✔ termfx $VERSION installed${C0}

  ${CB}Open a new terminal${C0} (or run ${CC}exec \$SHELL${C0}) to see the animated header.
  It needs a window of about ${CB}80×24${C0} or more; below that the header hides itself.
  If p10k or oh-my-posh is still active (--keep-old), keep only one prompt tool.

  ${CB}What's ready${C0}
EOF
  _tool_line python3   python3
  _tool_line starship  starship
  _tool_line fastfetch fastfetch
  _tool_line eza       eza
  { have bat || have batcat; } && printf '    %s✔%s %-12s ready\n' "$CG" "$C0" "bat" \
    || printf '    %s·%s %-12s not installed (optional)\n' "$CD" "$C0" "bat"
  _tool_line fzf       fzf
  local n_pal; n_pal=$("$BIN_DIR/termfx-engine" list palettes 2>/dev/null | grep -c .)
  cat <<EOF

  ${CB}Features & commands${C0}
EOF
  _cmd "termfx effect list"                 "list all animated effects"
  _cmd "termfx effect next"                 "cycle through effects live"
  _cmd "termfx effect info NAME"            "details + recommended palette"
  _cmd "termfx palette list"                "${n_pal:-?} colour palettes"
  _cmd "termfx palette show NAME"           "preview colours with gradient"
  _cmd "termfx palette next"                "cycle through palettes"
  _cmd "termfx preview effect=fire"         "full-screen preview (any key exits)"
  _cmd "termfx theme list"                  "change shell/prompt colours"
  _cmd "termfx starship theme list"         "browse named prompt themes"
  _cmd "termfx starship theme cloud-ops"    "apply a Starship theme"
  _cmd "termfx art add mine"                "paste your own ASCII art"
  _cmd "termfx info items"                  "manage the system info panel"
  _cmd "termfx info custom 'CMD'"           "custom info panel command"
  _cmd "termfx randomize"                   "instant random look"
  _cmd "termfx profile save work"           "save/load config profiles"
  _cmd "termfx --help"                      "full feature list"
  cat <<EOF

  ${CB}All effects${C0} (descriptions and recommended palettes):
EOF
  "$BIN_DIR/termfx" effect list
  cat <<EOF

  ${CB}All palettes${C0} (colour stop count and hex values):
EOF
  "$BIN_DIR/termfx-engine" list palette-details
  local n_st n_ff
  n_st=$(python3 "$BIN_DIR/termfx-themes" --list starship 2>/dev/null | grep -c .)
  n_ff=$(python3 "$BIN_DIR/termfx-themes" --list fetch 2>/dev/null | grep -c .)
  cat <<EOF

  ${CB}Quick tips${C0}
EOF
  _cmd "termfx starship theme developer-forge" "one of ${n_st:-?} Starship themes"
  _cmd "termfx starship set right_prompt true" "customize Starship controls"
  _cmd "termfx fastfetch gamer"                "one of ${n_ff:-?} info panel presets"
  _cmd "termfx glitch on"                      "random glitch distortions"
  _cmd "termfx info-colors neon"               "colour the info panel"
  _cmd "termfx set sparkle true"               "sparkle effect on the header"
  _cmd "termfx set vignette true"              "cinematic edge darkening"
  _cmd "termfx rotate on 60"                   "auto-rotate effects every 60s"
  _cmd "termfx align center"                   "centre the header"
  cat <<EOF

  Restore old setup:  ${CC}termfx restore${C0}
  Uninstall:          ${CC}termfx uninstall${C0}
  Something wrong?:   ${CC}termfx doctor${C0}
EOF
  case ":$PATH:" in *":$BIN_DIR:"*) ;; *) warn "$BIN_DIR is not in your PATH yet - it will be after you open a new terminal." ;; esac
}
