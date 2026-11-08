# shellcheck shell=bash
# help.sh - short help by default; one topic at a time for details.

# ---------------------------------------------------------------------------
# ONE table describes every setting:  name ; config key ; how to change it
# `termfx help` and `termfx status` both render from it, so they always agree.
# ---------------------------------------------------------------------------
SETTINGS_TABLE='
#Header
header;enabled;on | off
art;art;NAME | N | list | random | add
effect;effect;NAME | list | next | prev | off
palette;palette;NAME | list | next | prev | "#hex,#hex"
align;align;left | center | right
rotate;rotate;on | off [SECS]
glitch;glitch;on | off
#Shell look
theme;theme;NAME | list | new NAME
prompt;prompt_style;STYLE | list | custom
prompt char;prompt_char;X  (any one character)
prompt lines;prompt_lines;1 | 2
prompt clock;clock;on | off | "%H:%M:%S"
#Info panel
info;info;on | off | refresh | custom "CMD"
fastfetch;fetch_preset;PRESET | list
info style;info_style;NAME | list
info colors;info_colors;NAME | list
info rows;info_rows;LIST | list
#Starship prompt
starship theme;starship_theme;NAME | list
starship module;starship_modules;list | on NAME | off NAME
starship set;;OPTION VALUE   (25+ options)
#Alerts
notify;notification;on | off [SECS]
'
_hw() { local c=${COLUMNS:-0}; ((c > 0)) || c=$(tput cols 2>/dev/null || echo 80); [[ $c =~ ^[0-9]+$ ]] || c=80; ((c > 100)) && c=100; ((c < 40)) && c=40; printf '%s' "$c"; }
_hrule() { local n=$1 s=""; while ((n-- > 0)); do s+="─"; done; printf '%s' "$s"; }
_hsec() { printf '\n  %s%s%s%s\n' "$B" "$M" "${*^^}" "$Z"; }
# one value, coloured by meaning, never wider than 16 characters
_hval() { # KEY -> "padded-coloured"
  local k=$1 v col="" shown
  v=$(cfg_get "$k")
  case $k in starship_modules) v="$(wc -w <<<"$v" | tr -d ' ') active" ;; esac
  case ${v,,} in
    "")          shown="(default)"; col=$D ;;
    true)        shown="on";  col=$G ;;
    false|off)   shown="off"; col=$D ;;
    *)           shown=$v ;;
  esac
  ((${#shown} > 16)) && shown="${shown:0:15}…"
  printf '%s%-16s%s' "$col" "$shown" "$Z"
}
# _settings_table  - every setting, grouped, with its live value
_settings_table() {
  local line name key how first=1 w; w=$(_hw)
  while IFS= read -r line; do
    [[ -n $line ]] || continue
    if [[ $line == \#* ]]; then
      _hsec "${line#\#}"
      if ((w >= 80)); then printf '  %s%-17s %-16s %s%s\n' "$D" "SETTING" "NOW" "VALUES  → termfx SETTING VALUE" "$Z"; fi
      continue
    fi
    IFS=';' read -r name key how <<<"$line"
    if ((w >= 80)); then
      local val; if [[ -n $key ]]; then val=$(_hval "$key"); else val=$(printf '%-16s' ""); fi
      printf '  %s%-17s%s %s %s%s%s\n' "$B" "$name" "$Z" "$val" "$C" "$how" "$Z"
    else
      local val; if [[ -n $key ]]; then val=$(_hval "$key"); else val=""; fi
      printf '  %s%-17s%s %s\n' "$B" "$name" "$Z" "$val"
      printf '  %s  └ termfx %s %s%s\n' "$D" "$name" "$how" "$Z"
    fi
  done <<<"$SETTINGS_TABLE"
}
# a "┃ command   what it does" row
_hcmd() { if (( $(_hw) >= 80 )); then printf '  %s┃%s  %s%-30s%s %s%s%s\n' "$M" "$Z" "$C" "$1" "$Z" "$D" "$2" "$Z"
          else printf '  %s┃%s  %s%s%s\n  %s┃%s  %s  %s%s\n' "$M" "$Z" "$C" "$1" "$Z" "$M" "$Z" "$D" "$2" "$Z"; fi; }

usage() {
  local run="${D}○ header not running in this terminal${Z}"
  [[ -n ${TERMFX_FLAG:-} && -r ${TERMFX_FLAG}.state ]] && run="${G}● header running${Z}"
  printf '\n  %s%stermfx%s %s   %s\n' "$B" "$M" "$Z" "$("$ENGINE" version 2>/dev/null)" "$run"
  printf '  %s%s%s\n' "$D" "$(_hrule $(( $(_hw) - 4 )))" "$Z"

  _hsec "One pattern for every setting"
  _hcmd "termfx NAME"            "show the current value and your choices"
  _hcmd "termfx NAME VALUE"      "change it (prints  NAME: old → new)"
  _hcmd "termfx NAME list"       "browse the choices, pick by name or number"
  _hcmd "termfx NAME next|prev"  "cycle through them live"
  _hcmd "termfx NAME on|off"     "switch it"
  printf '  %s%s  example:%s  %stermfx effect%s  →  %stermfx effect fire%s  →  %stermfx effect next%s\n' "$M" "┃" "$Z" "$C" "$Z" "$C" "$Z" "$C" "$Z"

  _settings_table

  _hsec "Do things"
  _hcmd "termfx preview effect=fire"  "try a look full-screen"
  _hcmd "termfx randomize"            "a surprise look"
  _hcmd "termfx profile save NAME"    "save | load | list | rm your looks"
  _hcmd "termfx export | import FILE" "share a look as a file"
  _hcmd "termfx undo"                 "revert your last change"
  _hcmd "termfx reload"               "re-read the config now"

  _hsec "Look & fix"
  _hcmd "termfx status"               "every setting + file locations"
  _hcmd "termfx get|set KEY VALUE"    "any raw config key (termfx keys)"
  _hcmd "termfx config"               "edit the config file"
  _hcmd "termfx doctor"               "find out what is wrong"
  _hcmd "termfx restore"              "bring back your old terminal setup"
  _hcmd "termfx uninstall"            "remove termfx"

  printf '\n  %sMore detail:%s %stermfx help art|header|look|starship|profiles|all%s\n\n' "$D" "$Z" "$C" "$Z"
}
usage_topic() {
  case $1 in
    art) cat <<EOT
${B}ART${Z}  (your own ASCII - any size)
  termfx art                            list art (● = in use)
  termfx art NAME|N                     use it (same as: art use NAME)
  termfx art use NAME|N|random          switch art (applies live)
  termfx art add NAME [-u]              paste art (Ctrl-D ends; -u = use it)
  termfx art add NAME FILE|URL [-u]     import a file or URL
  termfx art edit NAME                  open in \$EDITOR (best for huge art)
  termfx art show NAME                  print it plainly
  termfx art rm NAME                    delete
  termfx art image NAME FILE|URL [W]    image to ASCII (needs chafa or jp2a)
  termfx art text NAME "TEXT" [font]    big text banner (needs figlet or toilet)
  termfx art distro [NAME]              your distro's logo (needs fastfetch)
  termfx art info [NAME]                size / fitting details
  Multi-frame animation: put a line  ---FRAME---  between frames.
EOT
    ;;
    header) cat <<EOT
${B}HEADER${Z}
  termfx effect [NAME|N|list|next|prev|off|on|info NAME]
  termfx palette [NAME|N|list|next|prev|show NAME|colors|"#hex,#hex"|white]
  termfx align [left|center|right]
  termfx rotate [on|off] [SECS]       termfx glitch [on|off]
  termfx on | off | reload            enable / disable / re-read config
  termfx preview [key=value ...]      full-screen try-out: preview effect=vortex
  Extra knobs:  termfx set sparkle true | vignette true | intensity 1.4
  Available effects:
$("$ENGINE" list effects | sed 's/^/    /')
EOT
    ;;
    look) cat <<EOT
${B}SHELL LOOK${Z}
  termfx theme [NAME|list|new NAME [BASE]|edit NAME]
  termfx prompt [STYLE|list|custom]
  termfx prompt char [X]    termfx prompt lines [1|2]    termfx prompt clock [on|off|"%H:%M:%S"]
  termfx info [on|off|refresh|custom "CMD"]
  termfx info style|colors|rows [VALUE|list]
  termfx fastfetch [list|PRESET]
  termfx look               show the current prompt look
  ${D}(older spellings still work: info-style, info-colors, info-rows, char, lines, clock)${Z}
EOT
    ;;
    starship) cat <<EOT
${B}STARSHIP${Z}
  termfx starship                       show options, theme, modules
  termfx starship theme [NAME|list]     named theme
  termfx starship preset NAME|list      module collection (balanced minimal developer cloud server full)
  termfx starship set OPTION VALUE      change one of 25+ options
  termfx starship module list|on NAME|off NAME
EOT
    ;;
    profiles) cat <<EOT
${B}PROFILES & SHARING${Z}
  termfx profile list|save NAME|load NAME|rm NAME
  termfx export [FILE]                  config to JSON (stdout or FILE)
  termfx import FILE [--trust]          from JSON (info_cmd/info_config need --trust)
  termfx randomize                      random effect + palette + art
  termfx undo                           revert the last change
EOT
    ;;
    all) usage; for t in art header look starship profiles; do echo; usage_topic "$t"; done ;;
    *) die "no help topic '$1' (art, header, look, starship, profiles, all)" ;;
  esac
}
