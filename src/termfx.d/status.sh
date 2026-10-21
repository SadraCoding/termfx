cmd_status() {
  say "${B}termfx${Z} $("$ENGINE" version 2>/dev/null)"
  for k in enabled art effect palette fit fps max_height info pause theme prompt_style; do
    printf '  %-12s %s\n' "$k" "$(cfg_get $k)"
  done
  if [[ -n ${TERMFX_FLAG:-} && -r ${TERMFX_FLAG}.state ]]; then
    say "  ${G}● header running in this terminal${Z}"
  else
    say "  ${D}○ header not running in this terminal${Z}"
    say "  ${D}  tip: open a new terminal ≥80×24, or run: termfx doctor${Z}"
  fi
}

