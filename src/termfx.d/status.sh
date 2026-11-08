# shellcheck shell=bash
# cmd_status - everything termfx currently does, where it lives, and how to change each part.
cmd_status() {
  local run="${D}○ header not running in this terminal${Z}"
  [[ -n ${TERMFX_FLAG:-} && -r ${TERMFX_FLAG}.state ]] && run="${G}● header running in this terminal${Z}"
  printf '\n  %s%stermfx%s %s   %s\n' "$B" "$M" "$Z" "$("$ENGINE" version 2>/dev/null)" "$run"
  printf '  %s%s%s\n' "$D" "$(_hrule $(( $(_hw) - 4 )))" "$Z"
  _settings_table
  _hsec "Files"
  _hcmd "termfx config"             "$CONF"
  _hcmd "art"                      "$ART_DIR"
  _hcmd "profiles"                 "$PROFILE_DIR"
  [[ -f $CONF_DIR/config.undo ]] && _hcmd "termfx undo"  "your last change can be reverted"
  [[ -n ${TERMFX_FLAG:-} && -r ${TERMFX_FLAG}.state ]] || printf '\n  %stip: open a new terminal of at least 80×24, or run: termfx doctor%s\n' "$D" "$Z"
  printf '\n  %severy setting works the same way:%s %stermfx NAME%s shows it, %stermfx NAME VALUE%s changes it, %stermfx help%s explains.\n\n' "$D" "$Z" "$C" "$Z" "$C" "$Z" "$C" "$Z"
}
