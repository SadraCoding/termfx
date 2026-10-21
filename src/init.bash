# termfx bash integration (managed by termfx - rerun the installer to refresh)
[[ $- == *i* ]] || return 0 2>/dev/null || true
TERMFX_HOME="${XDG_CONFIG_HOME:-$HOME/.config}/termfx"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac

# ---- settings (one awk instead of many forks)
TFX_UI=true TFX_PROMPT=auto TFX_ICONS=true TFX_NOTIFY=false TFX_NOTIFY_AFTER=10
[[ -r $TERMFX_HOME/config ]] && eval "$(awk -F= '/^[ \t]*(ui|prompt|icons|notification|notify_after)[ \t]*=/ { k=$1; v=$2; sub(/#.*/,"",v); gsub(/[^A-Za-z0-9_.\/-]/,"",v); gsub(/[ \t]/,"",k); printf "TFX_%s=%s;", toupper(k), v }' "$TERMFX_HOME/config")"

# ---- UI: aliases, fzf, starship
if [[ $TFX_UI != false ]]; then
  if command -v eza >/dev/null 2>&1; then
    _tfx_ic=; [[ $TFX_ICONS == true ]] && _tfx_ic=--icons
    alias ls="eza $_tfx_ic --group-directories-first"
    alias ll="eza -lh $_tfx_ic --git --group-directories-first"
    alias la="eza -lah $_tfx_ic --git --group-directories-first"
    alias tree="eza --tree $_tfx_ic"
    unset _tfx_ic
  else
    alias ls='ls --color=auto'; alias ll='ls -lh'; alias la='ls -lAh'
  fi
  if ! command -v bat >/dev/null 2>&1 && command -v batcat >/dev/null 2>&1; then alias bat=batcat; fi
  export BAT_THEME=ansi
  if command -v fzf >/dev/null 2>&1; then
    export FZF_DEFAULT_OPTS="--height 40% --layout=reverse --border rounded --color=bg+:#313244,fg+:#cdd6f4,hl:#89b4fa,hl+:#89b4fa,pointer:#89b4fa,prompt:#89b4fa,info:#a6adc8"
    if fzf --bash >/dev/null 2>&1; then eval "$(fzf --bash)"
    else
      for _tfx_f in /usr/share/fzf/key-bindings.bash /usr/share/doc/fzf/examples/key-bindings.bash /usr/share/fzf/shell/key-bindings.bash ~/.fzf/shell/key-bindings.bash; do
        [[ -r $_tfx_f ]] && { . "$_tfx_f"; break; }
      done
      for _tfx_f in /usr/share/fzf/completion.bash /usr/share/doc/fzf/examples/completion.bash /usr/share/bash-completion/completions/fzf ~/.fzf/shell/completion.bash; do
        [[ -r $_tfx_f ]] && { . "$_tfx_f"; break; }
      done
      unset _tfx_f
    fi
  fi
fi
if [[ $TFX_PROMPT != off ]] && command -v starship >/dev/null 2>&1 && [[ -z ${POSH_THEME:-} ]] && ! declare -F p10k >/dev/null 2>&1; then
  # The managed prompt must follow `termfx starship theme`; choose the no-icon variant when requested.
  if [[ $TFX_ICONS == false && -r $TERMFX_HOME/starship-plain.toml ]]; then export STARSHIP_CONFIG="$TERMFX_HOME/starship-plain.toml"
  elif [[ -r $TERMFX_HOME/starship.toml ]]; then export STARSHIP_CONFIG="$TERMFX_HOME/starship.toml"; fi
  eval "$(starship init bash)"
fi

# ---- animated header
__termfx_cls() { local p h=0 par; [[ -r ${TERMFX_FLAG:-/nonexistent}.state ]] && read -r p h par < "$TERMFX_FLAG.state"; [[ $h =~ ^[0-9]+$ ]] || h=0; printf '\e[2J\e[%d;1H' $((h+1)); }
clear() { if [[ -n ${TERMFX_FLAG:-} ]]; then __termfx_cls; else command clear "$@"; fi; }

__termfx_preexec() {
  __TFX_CMD_START=$SECONDS
  [[ -n ${TERMFX_FLAG:-} ]] || return 0
  case ${__TFX_MODE:-tui} in never) return 0 ;; always) : > "$TERMFX_FLAG"; return 0 ;; esac
  local -a w; read -ra w <<<"$1"
  local i=0
  while ((i < ${#w[@]})); do
    case ${w[i]##*/} in sudo|doas|command|env|exec|nohup|time|builtin|nice|setsid|-*|*=*) i=$((i+1)) ;; *) break ;; esac
  done
  local c=${w[i]:-}; c=${c##*/}
  [[ -n $c && ${__TFX_CMDS:-} == *",$c,"* ]] && : > "$TERMFX_FLAG"
  return 0
}
__termfx_post() {
  [[ -e ${TERMFX_FLAG:-/nonexistent} ]] && rm -f -- "$TERMFX_FLAG"
  if [[ ${TFX_NOTIFY} == true && -n ${__TFX_CMD_START:-} ]] && (( SECONDS - __TFX_CMD_START >= TFX_NOTIFY_AFTER )); then
    local elapsed=$(( SECONDS - __TFX_CMD_START ))
    command -v notify-send >/dev/null 2>&1 && notify-send -t 5000 "termfx" "Command finished (${elapsed}s)" 2>/dev/null &
  fi
  __TFX_CMD_START=
  __TFX_READY=1
}
__termfx_debug() {
  [[ -n ${__TFX_READY:-} ]] || return 0
  [[ -n ${COMP_LINE:-} ]] && return 0
  __TFX_READY=
  __termfx_preexec "$BASH_COMMAND"
}
__termfx_exit() { [[ -n ${TERMFX_FLAG:-} ]] && rm -f -- "$TERMFX_FLAG" "$TERMFX_FLAG.state"; printf '\e[r'; }
__termfx_ctrl_l() { __termfx_cls; printf '%s%s' "${PS1@P}" "$READLINE_LINE"; }

__termfx_hooks() {
  if declare -F __bp_precmd_invoke_cmd >/dev/null 2>&1; then          # bash-preexec present
    preexec_functions+=(__termfx_preexec); precmd_functions+=(__termfx_post)
  else
    [[ -z $(trap -p DEBUG) ]] && trap '__termfx_debug' DEBUG
    if [[ $(declare -p PROMPT_COMMAND 2>/dev/null) == "declare -a"* ]]; then PROMPT_COMMAND+=(__termfx_post)
    else PROMPT_COMMAND="${PROMPT_COMMAND:+${PROMPT_COMMAND%;}; }__termfx_post"; fi
  fi
  [[ -z $(trap -p EXIT) ]] && trap '__termfx_exit' EXIT
  if (( BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 4) )); then
    bind -x '"\C-l": __termfx_ctrl_l' 2>/dev/null
  fi
}

__termfx_boot() {
  [[ -z ${TERMFX_DISABLE:-} && -t 1 ]] || return 0
  case ${TERM:-dumb} in linux|dumb|"") return 0 ;; esac
  [[ -x $HOME/.local/bin/termfx-engine ]] || return 0
  if [[ -n ${TERMFX_ACTIVE:-} ]]; then                                  # `exec bash` inside a running header
    local p h par
    [[ -r ${TERMFX_FLAG:-/nonexistent}.state ]] && read -r p h par < "$TERMFX_FLAG.state"
    if [[ ${par:-} == "$$" ]] && kill -0 "${p:-0}" 2>/dev/null; then __termfx_hooks; fi
    return 0
  fi
  export TERMFX_SEED=$RANDOM$RANDOM
  local out h rows cols mode cmds tip
  out=$(command termfx-engine height 2>/dev/null) || return 0
  read -r h rows cols mode cmds <<<"$out"
  if ! [[ ${h:-0} =~ ^[0-9]+$ ]] || (( h <= 0 )); then
    tip="${XDG_CACHE_HOME:-$HOME/.cache}/termfx/.hint-size"
    if [[ ! -f $tip && -t 2 ]] && [[ ${cols:-0} =~ ^[0-9]+$ && ${rows:-0} =~ ^[0-9]+$ ]] \
       && (( cols > 0 && (cols < 80 || rows < 24) )); then
      mkdir -p "$(dirname "$tip")" 2>/dev/null || true
      : > "$tip" 2>/dev/null || true
      printf 'termfx: header hidden (terminal %sx%s is small). Resize to ~80x24, or run: termfx doctor\n' "$cols" "$rows" >&2
    fi
    return 0
  fi
  __TFX_MODE=${mode:-tui}; __TFX_CMDS=",${cmds:-},"
  export TERMFX_FLAG="${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}/termfx-$UID-$$" TERMFX_ACTIVE=1
  rm -f -- "$TERMFX_FLAG" "$TERMFX_FLAG.state"
  printf '\e[2J\e[%d;%dr\e[%d;1H' $((h+1)) "${rows:-${LINES:-40}}" $((h+1))
  ( command termfx-engine run "$TERMFX_FLAG" $$ </dev/null >/dev/null 2>&1 & )
  __termfx_hooks
}
__termfx_boot
