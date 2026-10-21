# termfx zsh integration (managed by termfx - rerun the installer to refresh)
[[ -o interactive ]] || return 0
typeset -g TERMFX_HOME="${XDG_CONFIG_HOME:-$HOME/.config}/termfx"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac

# ---- settings (one awk instead of many forks)
TFX_UI=true TFX_PROMPT=auto TFX_ICONS=true TFX_NOTIFY=false TFX_NOTIFY_AFTER=10
[[ -r $TERMFX_HOME/config ]] && eval "$(awk -F= '/^[ \t]*(ui|prompt|icons|notification|notify_after)[ \t]*=/ { k=$1; v=$2; sub(/#.*/,"",v); gsub(/[^A-Za-z0-9_.\/-]/,"",v); gsub(/[ \t]/,"",k); printf "TFX_%s=%s;", toupper(k), v }' "$TERMFX_HOME/config")"

# ---- UI: aliases, fzf, starship
if [[ $TFX_UI != false ]]; then
  if (( $+commands[eza] )); then
    local _ic=; [[ $TFX_ICONS == true ]] && _ic=--icons
    alias ls="eza $_ic --group-directories-first"
    alias ll="eza -lh $_ic --git --group-directories-first"
    alias la="eza -lah $_ic --git --group-directories-first"
    alias tree="eza --tree $_ic"
  else
    alias ls='ls --color=auto'; alias ll='ls -lh'; alias la='ls -lAh'
  fi
  (( $+commands[batcat] && ! $+commands[bat] )) && alias bat=batcat
  export BAT_THEME=ansi
  if (( $+commands[fzf] )); then
    export FZF_DEFAULT_OPTS="--height 40% --layout=reverse --border rounded --color=bg+:#313244,fg+:#cdd6f4,hl:#89b4fa,hl+:#89b4fa,pointer:#89b4fa,prompt:#89b4fa,info:#a6adc8"
    if fzf --zsh >/dev/null 2>&1; then source <(fzf --zsh)
    else
      local _f
      for _f in /usr/share/fzf/key-bindings.zsh /usr/share/doc/fzf/examples/key-bindings.zsh /usr/share/fzf/shell/key-bindings.zsh ~/.fzf/shell/key-bindings.zsh; do
        [[ -r $_f ]] && { source $_f; break; }
      done
      for _f in /usr/share/fzf/completion.zsh /usr/share/doc/fzf/examples/completion.zsh /usr/share/fzf/shell/completion.zsh ~/.fzf/shell/completion.zsh; do
        [[ -r $_f ]] && { source $_f; break; }
      done
    fi
  fi
fi
if [[ $TFX_PROMPT != off ]] && (( $+commands[starship] )) && (( ! $+functions[p10k] )) && [[ -z ${POSH_THEME:-} ]]; then
  # The managed prompt must follow `termfx starship theme`; choose the no-icon variant when requested.
  if [[ $TFX_ICONS == false && -r $TERMFX_HOME/starship-plain.toml ]]; then export STARSHIP_CONFIG="$TERMFX_HOME/starship-plain.toml"
  elif [[ -r $TERMFX_HOME/starship.toml ]]; then export STARSHIP_CONFIG="$TERMFX_HOME/starship.toml"; fi
  eval "$(starship init zsh)"
fi

# ---- animated header
_termfx_cls() { local p h=0 par; [[ -r ${TERMFX_FLAG:-/nonexistent}.state ]] && read -r p h par < "$TERMFX_FLAG.state"; [[ $h == <-> ]] || h=0; print -n "\e[2J\e[$((h+1));1H"; }
clear() { if [[ -n ${TERMFX_FLAG:-} ]]; then _termfx_cls; else command clear "$@"; fi }
_termfx_widget_cls() { _termfx_cls; zle reset-prompt }

_termfx_preexec() {
  _TFX_CMD_START=$SECONDS
  [[ -n ${TERMFX_FLAG:-} ]] || return
  case $_TFX_MODE in never) return ;; always) : >| "$TERMFX_FLAG"; return ;; esac
  local -a w; w=(${(z)1})
  while (( ${#w} )); do
    case ${w[1]:t} in
      sudo|doas|command|env|exec|nohup|time|noglob|builtin|nice|setsid|-*|*=*) shift w ;;
      *) break ;;
    esac
  done
  [[ -n ${w[1]:-} && $_TFX_CMDS == *",${w[1]:t},"* ]] && : >| "$TERMFX_FLAG"
}
_termfx_precmd() {
  [[ -e ${TERMFX_FLAG:-/nonexistent} ]] && command rm -f -- "$TERMFX_FLAG"
  # notification for long-running commands
  if [[ ${TFX_NOTIFY} == true && -n ${_TFX_CMD_START:-} ]] && (( SECONDS - _TFX_CMD_START >= TFX_NOTIFY_AFTER )); then
    local elapsed=$(( SECONDS - _TFX_CMD_START ))
    if command -v notify-send >/dev/null 2>&1; then
      notify-send -t 5000 "termfx" "Command finished (${elapsed}s)" 2>/dev/null &
    fi
  fi
  _TFX_CMD_START=
}
_termfx_zshexit() { [[ -n ${TERMFX_FLAG:-} ]] && command rm -f -- "$TERMFX_FLAG" "$TERMFX_FLAG.state"; print -n '\e[r'; }

_termfx_hooks() {
  autoload -Uz add-zsh-hook
  add-zsh-hook preexec _termfx_preexec
  add-zsh-hook precmd _termfx_precmd
  add-zsh-hook zshexit _termfx_zshexit
  zle -N _termfx_widget_cls
  bindkey '^L' _termfx_widget_cls
  bindkey -M viins '^L' _termfx_widget_cls 2>/dev/null
  bindkey -M vicmd '^L' _termfx_widget_cls 2>/dev/null
}

_termfx_boot() {
  emulate -L zsh
  [[ -z ${TERMFX_DISABLE:-} && -t 1 && ${TERM:-dumb} != (linux|dumb) ]] || return 0
  [[ -x $HOME/.local/bin/termfx-engine ]] || return 0
  if [[ -n ${TERMFX_ACTIVE:-} ]]; then          # `exec zsh` inside a running header
    local p h par
    [[ -r ${TERMFX_FLAG:-/nonexistent}.state ]] && read -r p h par < "$TERMFX_FLAG.state"
    if [[ ${par:-} == $$ ]] && kill -0 ${p:-0} 2>/dev/null; then _termfx_hooks; fi
    return 0
  fi
  export TERMFX_SEED=$RANDOM$RANDOM
  local out; out=$(command termfx-engine height 2>/dev/null) || return 0
  local -a f; f=(${=out})
  local h=${f[1]:-0} rows=${f[2]:-$LINES} cols=${f[3]:-$COLUMNS}
  if (( h <= 0 )); then
    # one-time tip when the terminal is simply too small for the header
    local tip="${XDG_CACHE_HOME:-$HOME/.cache}/termfx/.hint-size"
    if [[ ! -f $tip && -t 2 ]] && (( ${cols:-0} > 0 && (cols < 80 || rows < 24) )); then
      mkdir -p "${tip:h}" 2>/dev/null || true
      : >| "$tip" 2>/dev/null || true
      print -u2 -P "%F{221}termfx:%f header hidden (terminal ${cols}x${rows} is small). Resize to ~80x24, or run: termfx doctor"
    fi
    return 0
  fi
  typeset -g _TFX_MODE=${f[4]:-tui} _TFX_CMDS=",${f[5]:-},"
  export TERMFX_FLAG="${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/termfx-$UID-$$" TERMFX_ACTIVE=1
  command rm -f -- "$TERMFX_FLAG" "$TERMFX_FLAG.state"
  printf '\e[2J\e[%d;%dr\e[%d;1H' $((h+1)) $rows $((h+1))
  ( command termfx-engine run "$TERMFX_FLAG" $$ </dev/null >/dev/null 2>&1 & )
  _termfx_hooks
}
_termfx_boot
