# shellcheck shell=bash
# completion.sh - "termfx completion bash|zsh" prints the scripts
cmd_completion() {
  case ${1:-} in
    bash)
        cat <<'COMPEOF'
_termfx_completions() {
    local cur words=(header art effect palette theme prompt starship info fastfetch notify align rotate glitch on off reload preview randomize profile export import undo status get set keys look config doctor restore uninstall version help completion stats)
  local TFX_ENG; TFX_ENG=$(command -v termfx-engine 2>/dev/null || echo "$HOME/.local/bin/termfx-engine")
  local TFX_THM; TFX_THM=$(command -v termfx-themes 2>/dev/null || echo "$HOME/.local/bin/termfx-themes")
  cur="${COMP_WORDS[COMP_CWORD]}"
  if [[ $COMP_CWORD == 1 ]]; then
    COMPREPLY=($(compgen -W "${words[*]}" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "effect" ]]; then
    COMPREPLY=($(compgen -W "list next prev info on off status $($TFX_ENG list effects 2>/dev/null | awk '{print $1}')" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "palette" ]]; then
    COMPREPLY=($(compgen -W "list next prev show colors auto $($TFX_ENG list color-names 2>/dev/null) $($TFX_ENG list palettes 2>/dev/null)" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "theme" ]]; then
    COMPREPLY=($(compgen -W "$($TFX_THM --list themes 2>/dev/null) list new edit" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "starship" && ${COMP_WORDS[2]} == "module" ]]; then
    if [[ ${COMP_WORDS[3]} == "on" || ${COMP_WORDS[3]} == "off" || ${COMP_WORDS[3]} == "enable" || ${COMP_WORDS[3]} == "disable" ]]; then
      COMPREPLY=($(compgen -W "$(termfx starship module list 2>/dev/null | awk '{print $2}')" -- "$cur"))
    else COMPREPLY=($(compgen -W "list on off enable disable" -- "$cur")); fi
  elif [[ ${COMP_WORDS[1]} == "starship" && ${COMP_WORDS[2]} == "theme" ]]; then
    COMPREPLY=($(compgen -W "list $(termfx-themes --list starship 2>/dev/null | awk '{print $1}')" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "starship" && ${COMP_WORDS[2]} == "preset" ]]; then
    COMPREPLY=($(compgen -W "list balanced minimal developer cloud server full" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "starship" && ${COMP_WORDS[2]} == "set" ]]; then
    COMPREPLY=($(compgen -W "$(termfx keys 2>/dev/null | sed -n 's/^starship_//p')" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "starship" ]]; then
    COMPREPLY=($(compgen -W "list show preset set module" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "art" ]]; then
    COMPREPLY=($(compgen -W "list add edit use show rm image text distro info" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "info" ]]; then
    COMPREPLY=($(compgen -W "on off refresh items custom status list style colors rows" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "prompt" ]]; then
    COMPREPLY=($(compgen -W "list custom char lines clock $($TFX_THM --list prompts 2>/dev/null | awk '{print $1}')" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "help" ]]; then
    COMPREPLY=($(compgen -W "art header look starship profiles all" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "profile" ]]; then
    COMPREPLY=($(compgen -W "list save load rm" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} =~ ^(on|off|header|glitch|rotate|notify)$ ]]; then
    COMPREPLY=($(compgen -W "on off" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "align" ]]; then
    COMPREPLY=($(compgen -W "left center right" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "fastfetch" ]]; then
    COMPREPLY=($(compgen -W "list $($TFX_THM --list fetch 2>/dev/null | awk '{print $1}')" -- "$cur"))
  elif [[ ${COMP_WORDS[1]} == "set" ]]; then
    COMPREPLY=($(compgen -W "$(termfx keys 2>/dev/null)" -- "$cur"))
  fi
}
complete -F _termfx_completions termfx
COMPEOF
      ;;
    zsh)
        cat <<'COMPEOF'
#compdef termfx
_termfx() {
  local -a commands effects palettes themes
  commands=(header art effect palette theme prompt starship info fastfetch notify align rotate glitch on off reload preview randomize profile export import undo status get set keys look config doctor restore uninstall version help completion stats)
  if (( CURRENT == 2 )); then
    _describe 'termfx command' commands
  elif [[ $words[2] == "effect" ]]; then
    _values 'effects' list next prev info on off status $(termfx-engine list effects 2>/dev/null | awk '{print $1}')
  elif [[ $words[2] == "palette" ]]; then
    _values 'palettes' list next prev show colors auto $(termfx-engine list color-names 2>/dev/null) $(termfx-engine list palettes 2>/dev/null)
  elif [[ $words[2] == "info" ]]; then
    _values 'info sub' on off refresh items custom status list style colors rows
  elif [[ $words[2] == "prompt" ]]; then
    _values 'prompt' list custom char lines clock $(termfx-themes --list prompts 2>/dev/null | awk '{print $1}')
  elif [[ $words[2] == "help" ]]; then
    _values 'topic' art header look starship profiles all
  elif [[ $words[2] == "profile" ]]; then
    _values 'profile' list save load rm
  elif [[ $words[2] == "align" ]]; then
    _values 'align' left center right
  elif [[ $words[2] == "fastfetch" ]]; then
    _values 'Fastfetch preset' list $(termfx-themes --list fetch 2>/dev/null | awk '{print $1}')
  elif [[ $words[2] == "theme" ]]; then
    _values 'themes' $(termfx-themes --list themes 2>/dev/null) list new edit
  elif [[ $words[2] == "starship" ]]; then
    if [[ $words[3] == "theme" ]]; then
      _values 'Starship theme' list $(termfx-themes --list starship 2>/dev/null | awk '{print $1}')
    elif [[ $words[3] == "module" ]]; then
      if [[ $words[4] == "on" || $words[4] == "off" || $words[4] == "enable" || $words[4] == "disable" ]]; then
        _values 'Starship module' $(termfx starship module list 2>/dev/null | awk '{print $2}')
      else
        _values 'module action' list on off enable disable
      fi
    elif [[ $words[3] == "preset" ]]; then
      _values 'Starship preset' list balanced minimal developer cloud server full
    elif [[ $words[3] == "set" ]]; then
      _values 'Starship option' $(termfx keys 2>/dev/null | sed -n 's/^starship_//p')
    else
      _values 'Starship command' list show preset set module
    fi
  elif [[ $words[2] == "art" ]]; then
    _values 'art sub' list add edit use show rm image text distro info
  fi
}
compdef _termfx termfx
COMPEOF
      ;;
    *) die "usage: termfx completion bash|zsh" ;;
  esac
}
