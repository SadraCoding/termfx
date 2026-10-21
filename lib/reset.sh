# lib/reset.sh - back up + reset old terminal customizations, and restore them
BACKUP_ROOT="$HOME/.termfx-backup"

# Everything that can fight with termfx. Only touches $HOME (and $ZDOTDIR), never /etc.
RESET_PATHS=(
  .bashrc .bash_profile .bash_login .profile .bash_aliases .bash_logout
  .zshrc .zprofile .zshenv .zlogin .zlogout .zsh_aliases '.zcompdump*'
  .p10k.zsh .oh-my-zsh .zinit .zplug .antigen .zsh .zim .zimrc .sheldon
  .config/starship.toml .config/oh-my-posh .config/ohmyposh
  .config/fastfetch .config/neofetch
  .config/ghostty .config/kitty .config/alacritty .config/wezterm
  .wezterm.lua .alacritty.yml .alacritty.toml
)

# zsh files that may live under $ZDOTDIR instead of $HOME
ZDOT_NAMES=(.zshrc .zprofile .zshenv .zlogin .zlogout .zsh_aliases .p10k.zsh)

write_clean_defaults() {
  local f
  for f in .bashrc .profile .bash_logout; do
    if [[ -r /etc/skel/$f ]]; then
      cp -- "/etc/skel/$f" "$HOME/$f"
    elif [[ $f == .bashrc ]]; then
      printf '%s\n' '# default ~/.bashrc' '[[ $- != *i* ]] && return' \
        "alias ls='ls --color=auto'" "alias ll='ls -lh'" "PS1='[\\u@\\h \\W]\\$ '" > "$HOME/$f"
    elif [[ $f == .profile ]]; then
      printf '%s\n' '# default ~/.profile' \
        '[ -n "$BASH_VERSION" ] && [ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc"' > "$HOME/$f"
    fi
  done

  # only recreate a zshrc when the user actually uses zsh - otherwise bash-only
  # users with zsh installed would get both shells patched by --shell auto
  local write_zsh=0 zrc="${ZDOTDIR:-$HOME}/.zshrc"
  case ${SHELL##*/} in zsh) write_zsh=1 ;; esac
  case ${SHELLS:-auto} in zsh|both) write_zsh=1 ;; esac
  if [[ -f $BACKUP_ROOT/latest/MANIFEST ]] && grep -qE '(^|/)\.zshrc$' "$BACKUP_ROOT/latest/MANIFEST" 2>/dev/null; then
    write_zsh=1
  fi
  if ((write_zsh)) && have zsh; then
    mkdir -p "$(dirname "$zrc")"
    printf '%s\n' '# default ~/.zshrc' \
      'HISTFILE=~/.zsh_history; HISTSIZE=10000; SAVEHIST=10000' \
      'setopt autocd histignoredups' \
      'autoload -Uz compinit && compinit' \
      "alias ls='ls --color=auto'" > "$zrc"
  fi
}

termfx_already_installed() {
  local f
  for f in "${ZDOTDIR:-$HOME}/.zshrc" "$HOME/.bashrc"; do
    [[ -f $f ]] && grep -qF "$MARK_BEGIN" "$f" && return 0
  done
  return 1
}

# collect paths under HOME matching RESET_PATHS, plus ZDOTDIR files outside HOME
_collect_reset_list() {
  local p f zd
  list=()
  shopt -s nullglob
  for p in "${RESET_PATHS[@]}"; do
    for f in "$HOME"/$p; do
      if [[ -e $f || -L $f ]]; then list+=("${f#"$HOME"/}"); fi
    done
  done
  shopt -u nullglob
  zd="${ZDOTDIR:-}"
  if [[ -n $zd && $zd != "$HOME" ]]; then
    for p in "${ZDOT_NAMES[@]}"; do
      f="$zd/$p"
      [[ -e $f || -L $f ]] || continue
      case $f in
        "$HOME"/*) list+=("${f#"$HOME"/}") ;;
        *)
          # store outside-HOME ZDOTDIR files under a dedicated backup folder
          list+=("__zdotdir__/$p")
          ;;
      esac
    done
  fi
}

reset_to_defaults() {
  local ts dest rel f p a gt=0
  local list=()
  # re-running the installer must never overwrite the backup of the user's ORIGINAL setup
  if termfx_already_installed && [[ ${RESET:-1} != 2 ]]; then
    info "termfx is already set up here - keeping your first backup untouched (use --reset to force)"
    return 0
  fi
  ts=$(date +%Y%m%d-%H%M%S); dest="$BACKUP_ROOT/$ts"
  _collect_reset_list

  # GNOME Terminal settings are only touched when there actually are some (and the user is told)
  if have dconf && [[ -n $(dconf dump /org/gnome/terminal/ 2>/dev/null) ]]; then gt=1; fi
  if ((${#list[@]} == 0 && gt == 0)); then
    info "nothing to reset - your terminal is already clean"; return 0
  fi
  info "these old customizations will be MOVED to a backup (nothing is deleted):"
  if ((${#list[@]})); then
    for rel in "${list[@]}"; do
      if [[ $rel == __zdotdir__/* ]]; then
        printf '     %s$ZDOTDIR/%s%s\n' "$CD" "${rel#__zdotdir__/}" "$C0"
      else
        printf '     %s~/%s%s\n' "$CD" "$rel" "$C0"
      fi
    done
  fi
  if ((gt)); then printf '     %sGNOME Terminal settings (profiles, colours, fonts)%s\n' "$CD" "$C0"; fi
  info "backup folder: $dest"
  a=$(ask "  Continue and reset to defaults? [Y/n]: " "y")
  [[ -z $a || $a == [Yy]* ]] || { warn "reset skipped - termfx may clash with your old setup"; return 0; }

  mkdir -p "$dest"; : > "$dest/MANIFEST"
  if [[ -n ${ZDOTDIR:-} && $ZDOTDIR != "$HOME" ]]; then
    printf '%s\n' "$ZDOTDIR" > "$dest/ZDOTDIR"
  fi
  for rel in ${list[@]+"${list[@]}"}; do
    if [[ $rel == __zdotdir__/* ]]; then
      mkdir -p "$dest/__zdotdir__"
      mv -- "${ZDOTDIR}/${rel#__zdotdir__/}" "$dest/$rel" && printf '%s\n' "$rel" >> "$dest/MANIFEST"
    else
      mkdir -p "$dest/$(dirname "$rel")"
      mv -- "$HOME/$rel" "$dest/$rel" && printf '%s\n' "$rel" >> "$dest/MANIFEST"
    fi
  done
  if ((gt)); then
    dconf dump /org/gnome/terminal/ > "$dest/gnome-terminal.dconf" 2>/dev/null || true
    dconf reset -f /org/gnome/terminal/ 2>/dev/null || true
  fi
  ln -sfn "$dest" "$BACKUP_ROOT/latest"
  [[ -e $BACKUP_ROOT/original ]] || ln -sfn "$dest" "$BACKUP_ROOT/original"
  write_clean_defaults
  ok "reset done. Restore anytime with:  termfx restore"
}

restore_backup() {
  local src=${1:-} rel f zd
  if [[ -z $src ]]; then if [[ -d $BACKUP_ROOT/original ]]; then src=$BACKUP_ROOT/original; else src=$BACKUP_ROOT/latest; fi; fi
  [[ -d $src && -f $src/MANIFEST ]] || { err "no backup found in $BACKUP_ROOT"; return 1; }
  src=$(readlink -f "$src")
  for f in "${ZDOTDIR:-$HOME}/.zshrc" "$HOME/.bashrc"; do
    [[ -f $f ]] && rc_patch "$f" uninstall "" 0 >/dev/null
  done
  zd="${ZDOTDIR:-}"
  [[ -f $src/ZDOTDIR ]] && zd=$(cat "$src/ZDOTDIR")
  while IFS= read -r rel; do
    [[ -n $rel ]] || continue
    if [[ $rel == __zdotdir__/* ]]; then
      [[ -n $zd ]] || continue
      rm -rf -- "${zd:?}/${rel#__zdotdir__/}"
      mkdir -p "$zd"
      cp -a -- "$src/$rel" "$zd/${rel#__zdotdir__/}"
    else
      rm -rf -- "${HOME:?}/$rel"
      mkdir -p "$(dirname "$HOME/$rel")"
      cp -a -- "$src/$rel" "$HOME/$rel"
    fi
  done < "$src/MANIFEST"
  if [[ -f $src/gnome-terminal.dconf ]] && have dconf; then dconf load /org/gnome/terminal/ < "$src/gnome-terminal.dconf"; fi
  ok "restored your old setup from $src - open a new terminal"
  info "termfx binaries may still be in ~/.local/bin - run  termfx uninstall  if you want those gone too"
}
