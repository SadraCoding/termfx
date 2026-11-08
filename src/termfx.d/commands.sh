# shellcheck shell=bash
# commands.sh - the settings commands. They all follow ONE pattern:
#
#   termfx NAME             show the current value and how to change it
#   termfx NAME VALUE       change it (prints  NAME: old -> new, then applies it)
#   termfx NAME list        browse the choices
#   termfx NAME next|prev   cycle through the choices      (effect, palette)
#   termfx NAME on|off      switch it                      (glitch, rotate, ...)
#   termfx undo             put back the config from before the last change

# pick KEY LABEL COMMAND-WORDS VALUE LISTCMD... - choose from a list (name or number); bare = show current
pick() {
  local k=$1 label=$2 words=$3 val=${4:-}; shift 4
  if [[ -z $val ]]; then
    show_current "$k" "$label" "change: termfx $words NAME   (name or list number)" "browse: termfx $words list"; return
  fi
  CHOOSE_CMD=$words choose "$k" "$val" "$@"
}
# flag KEY NAME ARG - on/off switch; bare = show current. Returns 1 when nothing was changed.
flag() {
  local k=$1 name=$2 a=${3:-} v
  [[ -n $a ]] || { show_current "$k" "$name" "change: termfx $name on|off"; return 1; }
  v=$(yesno "$a"); [[ -n $v ]] || die "usage: termfx $name on|off"
  change "$k" "$v"
}
# cycle KEY LISTCMD DIR [skip-first-as-default] - step through a list of names
cycle() {
  local k=$1 dir=$2 all=$3 cur idx total new
  cur=$(cfg_get "$k"); [[ -z $cur || $cur == auto ]] && cur=$(head -n1 <<<"$all")
  idx=$(grep -nx -- "$cur" <<<"$all" | cut -d: -f1 | head -n1); [[ $idx =~ ^[0-9]+$ ]] || idx=1
  total=$(wc -l <<<"$all")
  if [[ $dir == next ]]; then idx=$(( (idx % total) + 1 )); else idx=$(( (idx - 2 + total) % total + 1 )); fi
  new=$(sed -n "${idx}p" <<<"$all")
  change "$k" "$new"; say "  ${D}[$idx/$total]${Z}"
}

cmd_effect() {
  local a=${1:-} cur prev all n
  case $a in
    "") show_current effect effect "change: termfx effect NAME | next | prev | off | on" "browse: termfx effect list     details: termfx effect info NAME     try first: termfx preview effect=NAME" ;;
    list|menu) "$ENGINE" menu effects ;;
    next|prev) cycle effect "$a" "$("$ENGINE" list effects | awk '{print $1}')"; regen ;;
    info) n=${2:-}; [[ -n $n ]] || die "usage: termfx effect info NAME"; "$ENGINE" effect-info "$n" ;;
    off|none|plain)
      cur=$(cfg_get effect)
      case ${cur,,} in off|none|plain|false|no|0|"") ;; *) cfg_set effect_prev "$cur" ;; esac
      change effect off; say "  ${D}still art, no animation - bring it back with: termfx effect on${Z}"; reload ;;
    on)
      cur=$(cfg_get effect)
      case ${cur,,} in off|none|plain|false|no|0|"") ;; *) say "${G}✔${Z} ${B}effect${Z} is already on ($cur)"; return 0 ;; esac
      prev=$(cfg_get effect_prev); [[ -n $prev ]] || prev=aurora
      change effect "$prev"; reload ;;
    status) cur=$(cfg_get effect); case ${cur,,} in off|none|plain|false|no|0) say "effect: off" ;; *) say "effect: on ($cur)" ;; esac ;;
    *) all=$("$ENGINE" list effects | awk '{print $1}')
       [[ $a =~ ^[0-9]+$ ]] && { n=$(sed -n "${a}p" <<<"$all"); [[ -n $n ]] || die "no effect number $a (termfx effect list)"; a=$n; }
       grep -qx -- "$a" <<<"$all" || die "unknown effect '$a' (termfx effect list)"
       change effect "$a"; regen ;;
  esac
}

cmd_palette() {
  local a=${1:-} n
  case $a in
    "") show_current palette palette "change: termfx palette NAME | next | prev | auto | white | \"#hex,#hex\"" "browse: termfx palette list     preview: termfx palette show NAME     colour names: termfx palette colors" ;;
    list|menu) "$ENGINE" menu palettes ;;
    colors|colours) "$ENGINE" menu colors ;;
    next|prev) cycle palette "$a" "$("$ENGINE" list palettes)"; regen ;;
    show) n=${2:-}; [[ -n $n ]] || die "usage: termfx palette show NAME"; "$ENGINE" palette-show "$n" ;;
    *) if [[ $a =~ ^[0-9]+$ ]]; then n=$("$ENGINE" list palettes | sort | sed -n "${a}p"); [[ -n $n ]] || die "no palette number $a (termfx palette list)"; a=$n; fi
       valid_palette "$a"; change palette "$a"; regen ;;
  esac
}

cmd_theme() {
  local a=${1:-} n f t pl theme_list
  case $a in
    "") pick theme theme theme "" ;;
    new) n=${2:?usage: termfx theme new NAME [BASE]}; valid_name "$n"; mkdir -p "$CONF_DIR/themes"
      f="$CONF_DIR/themes/$n.json"; [[ -e $f ]] && die "$f exists"
      theme_list=$("$THEMES" --list themes); grep -qx "${3:-catppuccin}" <<<"$theme_list" || die "unknown base theme '${3:-catppuccin}' (termfx theme list)"
      python3 "$THEMES" --dump "${3:-catppuccin}" > "$f.tmp" && mv "$f.tmp" "$f" || { rm -f "$f.tmp"; die "could not create $f"; }
      ok "created $f - edit the colours, then: termfx theme $n" ;;
    edit) n=${2:?usage: termfx theme edit NAME}; ${VISUAL:-${EDITOR:-nano}} "$CONF_DIR/themes/$n.json"; regen ;;
    *) CHOOSE_CMD=theme choose theme "$a" "$THEMES" --list themes
       if [[ $a != list ]]; then
         t=$(cfg_get theme); pl=$("$ENGINE" list palettes)
         if grep -qx -- "$t" <<<"$pl"; then change palette "$t"; say "  ${D}header palette matched to the theme${Z}"; reload
         else warn "theme '$t' has no matching header palette - prompt colours updated; try: termfx palette list"; fi
       fi ;;
  esac
}

cmd_prompt() {
  local a=${1:-}
  case $a in
    "") pick prompt_style prompt prompt "" ;;
    list) pick prompt_style prompt prompt list "$THEMES" --list prompts ;;
    custom) change prompt_style custom; cfg_set starship_theme terminal-match
      say "  ${D}edit your own prompt in $CONF_DIR/starship.toml${Z}"; regen ;;
    char) cmd_char "${2:-}" ;;
    lines) cmd_lines "${2:-}" ;;
    clock) shift; cmd_clock "$@" ;;
    *) pick prompt_style prompt prompt "$a" "$THEMES" --list prompts ;;
  esac
}
cmd_char() {
  [[ -n ${1:-} ]] || { show_current prompt_char "prompt char" 'change: termfx prompt char "❯"'; return; }
  change prompt_char "$1"; regen
}
cmd_lines() {
  [[ -n ${1:-} ]] || { show_current prompt_lines "prompt lines" "change: termfx prompt lines 1|2"; return; }
  [[ $1 == 1 || $1 == 2 ]] || die "usage: termfx prompt lines 1|2"
  change prompt_lines "$1"; regen
}
cmd_clock() {
  local a=${1:-} v
  if [[ -z $a ]]; then show_current clock "prompt clock" "change: termfx prompt clock on|off|\"%H:%M:%S\"" "format: $(cfg_get clock_format)"; return; fi
  v=$(yesno "$a")
  if [[ -n $v ]]; then change clock "$v"; else change clock true; change clock_format "$a"; fi
  regen
}

cmd_look() {
  say "${B}prompt look${Z}"
  local k; for k in theme prompt_style prompt_char prompt_lines clock clock_format info_style info_rows; do printf '  %-13s %s\n' "$k" "$(cfg_get $k)"; done
}

cmd_info() {
  local a=${1:-status} mode cmd gap rows_val
  case $a in
    on) change info auto; reload ;;
    off) change info off; reload ;;
    refresh) rm -f "$CACHE_DIR/info.json" 2>/dev/null; ok "info cache cleared, will refresh"; reload ;;
    items|list) say "available rows: $("$THEMES" --list rows)"; say "${D}choose with: termfx info rows user,distro,cpu,memory${Z}" ;;
    custom) shift; [[ $# -ge 1 ]] || die "usage: termfx info custom \"COMMAND\""
      change info_cmd "$*"; cfg_set info auto; reload ;;
    style) shift; pick info_style "info style" "info style" "${1:-}" "$THEMES" --list infos ;;
    colors|colours) cmd_info_colors "${2:-}" ;;
    rows) shift; cmd_info_rows "$@" ;;
    status)
      mode=$(cfg_get info); cmd=$(cfg_get info_cmd); gap=$(cfg_get info_gap); rows_val=$(cfg_get info_rows)
      say "${B}info panel${Z}: ${mode:-auto}"
      say "  ${B}cmd${Z}    ${cmd:-(none, using auto/builtin)}"
      say "  ${B}gap${Z}    $gap columns"
      say "  ${B}style${Z}  $(cfg_get info_style)      ${D}termfx info style list${Z}"
      say "  ${B}colors${Z} $(cfg_get info_colors)      ${D}termfx info colors list${Z}"
      say "  ${B}rows${Z}   ${rows_val:-(default)}      ${D}termfx info rows list${Z}"
      say "  ${D}change: termfx info on|off|refresh|custom \"CMD\"${Z}" ;;
    *) die "usage: termfx info [on|off|refresh|custom CMD|style X|colors X|rows X]" ;;
  esac
}
cmd_info_colors() {
  case ${1:-} in
    "") show_current info_colors "info colors" "change: termfx info colors auto|rainbow|off|PALETTE" "browse: termfx info colors list" ;;
    list|menu) "$ENGINE" menu info-colors ;;
    auto|rainbow|off) change info_colors "$1"; regen ;;
    *) valid_palette "$1"; change info_colors "$1"; regen ;;
  esac
}
cmd_info_rows() {
  case ${1:-} in
    "") show_current info_rows "info rows" "change: termfx info rows user,distro,cpu,memory | default" "browse: termfx info rows list" ;;
    list) say "available: $("$THEMES" --list rows)"; say "${D}current: $(cfg_get info_rows)${Z}" ;;
    default) change info_rows ""; regen ;;
    *) change info_rows "$*"; regen ;;
  esac
}

cmd_align() {
  case ${1:-} in
    "") show_current align align "change: termfx align left|center|right" ;;
    left|center|right) change align "$1"; reload ;;
    *) die "usage: termfx align left|center|right" ;;
  esac
}
cmd_rotate() {
  flag rotate rotate "${1:-}" || return 0
  [[ -n ${2:-} ]] && change rotate_interval "$2"
  [[ ${1:-} == on || ${1:-} == true ]] && say "  ${D}every $(cfg_get rotate_interval)s (change: termfx rotate on SECS)${Z}"
  reload
}
cmd_notify() {
  flag notification notify "${1:-}" || return 0
  [[ -n ${2:-} ]] && change notify_after "$2"
  [[ ${1:-} == on || ${1:-} == true ]] && say "  ${D}after commands longer than $(cfg_get notify_after)s (change: termfx notify on SECS)${Z}"
  reload
}

cmd_set() {
  local k=${1:-}
  [[ $# -ge 2 ]] || die "usage: termfx set KEY VALUE   (all keys: termfx keys)"
  shift; [[ " $KNOWN_KEYS " == *" $k "* ]] || die "unknown key '$k' (see: termfx keys)"
  change "$k" "$*"; reload
}
cmd_get() {
  [[ -n ${1:-} ]] || { cmd_status; return; }
  cfg_get "$1"
}

cmd_undo() {
  [[ -f $CONF_DIR/config.undo ]] || die "nothing to undo yet"
  local tmp; tmp=$(mktemp "$CONF_DIR/.undo.XXXXXX"); cp -- "$CONF" "$tmp"
  cp -- "$CONF_DIR/config.undo" "$CONF"; mv -- "$tmp" "$CONF_DIR/config.undo"
  ok "config restored to how it was before the last change ${D}(run termfx undo again to redo)${Z}"; regen
}

cmd_profile() {
  local a=${1:-list} n f found; mkdir -p "$PROFILE_DIR"
  case $a in
    save) n=${2:?usage: termfx profile save NAME}; valid_name "$n"; cp -- "$CONF" "$PROFILE_DIR/$n.conf"; ok "profile '$n' saved  ${D}($PROFILE_DIR/$n.conf)${Z}" ;;
    load|use) n=${2:?usage: termfx profile load NAME}; valid_name "$n"
      [[ -f $PROFILE_DIR/$n.conf ]] || die "profile '$n' not found (termfx profile list)"
      snapshot; cp -- "$PROFILE_DIR/$n.conf" "$CONF"; ok "profile '$n' loaded  ${D}(undo with: termfx undo)${Z}"; regen ;;
    list)
      shopt -s nullglob; found=0
      for f in "$PROFILE_DIR"/*.conf; do found=1; n=${f##*/}; printf '  %s %s\n' "${G}●${Z}" "${n%.conf}"; done
      shopt -u nullglob
      ((found)) || say "  ${D}(no profiles yet - save one with: termfx profile save NAME)${Z}" ;;
    rm|remove|delete) n=${2:?usage: termfx profile rm NAME}; valid_name "$n"
      [[ -f $PROFILE_DIR/$n.conf ]] || die "profile '$n' not found (termfx profile list)"; rm -f -- "$PROFILE_DIR/$n.conf"; ok "profile '$n' removed" ;;
    *) die "usage: termfx profile list|save NAME|load NAME|rm NAME" ;;
  esac
}

cmd_export() {
  local dest=${1:-} json
  json=$(for k in $KNOWN_KEYS; do printf '%s\0%s\0' "$k" "$(cfg_get "$k")"; done |
    python3 -c 'import json,sys; p=sys.stdin.buffer.read().decode().split("\0")[:-1]; print(json.dumps(dict(zip(p[::2], p[1::2])), indent=2, ensure_ascii=False))')
  if [[ -n $dest ]]; then printf '%s\n' "$json" > "$dest"; ok "exported to $dest"
  else printf '%s\n' "$json"; fi
}

cmd_import() {
  local trust=0 src="" skipped a
        for a in "$@"; do case $a in --trust) trust=1 ;; *) src=$a ;; esac; done
    [[ -n $src ]] || die "usage: termfx import FILE [--trust]"
    [[ -f $src ]] || die "file not found: $src"
    snapshot
    # A shared file must not be able to run commands on this machine: info_cmd / info_config are skipped unless --trust.
    skipped=$(KNOWN="$KNOWN_KEYS" TRUST=$trust python3 -c '
import json, os, sys
d = json.load(open(sys.argv[1]))
if not isinstance(d, dict):
    sys.exit(2)
known = set(os.environ["KNOWN"].split())
risky = {"info_cmd", "info_config"}
trust = os.environ["TRUST"] == "1"
out, skipped = [], []
for k, v in d.items():
    v = str(v)
    if k not in known or "\n" in v or "\r" in v:
        skipped.append(k); continue
    if k in risky and not trust:
        skipped.append(k); continue
    out.append((k, v))
conf = sys.argv[2]
keep = []
try:
    for line in open(conf, encoding="utf-8"):
        k = line.split("=", 1)[0].strip() if "=" in line else ""
        if k not in {a for a, _ in out}:
            keep.append(line)
except OSError:
    pass
for k, v in out:
    keep.append("%s = %s\n" % (k, ("\"%s\"" % v) if "#" in v else v))
open(conf, "w", encoding="utf-8").writelines(keep)
print(" ".join(skipped))
' "$src" "$CONF") || die "import failed (invalid JSON?)"
    ok "config imported from $src"
    [[ -z $skipped ]] || warn "skipped: $skipped  (command-running or unknown keys; use --trust only for files you wrote yourself)"
  regen
}

cmd_randomize() {
  local all_fx all_pal rfx rpal arts f a
  mapfile -t all_fx < <("$ENGINE" list effects 2>/dev/null | awk '{print $1}' | grep -v random)
  mapfile -t all_pal < <("$ENGINE" list palettes 2>/dev/null)
  rfx=${all_fx[RANDOM % ${#all_fx[@]}]:-aurora}
  rpal=${all_pal[RANDOM % ${#all_pal[@]}]:-auto}
  arts=(); shopt -s nullglob; for f in "$ART_DIR"/*.txt; do a=${f##*/}; arts+=("${a%.txt}"); done; shopt -u nullglob
  ((${#arts[@]})) && change art "${arts[$((RANDOM % ${#arts[@]}))]}"
  change effect "$rfx"; change palette "$rpal"
  change intensity "$(awk "BEGIN{srand($RANDOM);printf \"%.1f\",0.6+rand()*1.2}")"
  change speed "$(awk "BEGIN{srand($RANDOM);printf \"%.1f\",0.5+rand()*2.0}")"
  ((RANDOM % 3 == 0)) && change sparkle true || change sparkle false
  ((RANDOM % 3 == 0)) && change vignette true || change vignette false
  say "  ${D}don't like it? termfx randomize again, or termfx undo${Z}"
  reload
}

cmd_config() {
  local ed=${VISUAL:-${EDITOR:-}}
  [[ ${1:-} == path ]] && { say "$CONF"; return; }
  if [[ -z $ed ]]; then for ed in nano vim vi; do command -v "$ed" >/dev/null 2>&1 && break; ed=; done; fi
  [[ -n $ed ]] || die "no editor found - set \$EDITOR or edit $CONF directly"
  say "${D}editing $CONF  (apply afterwards with: termfx reload)${Z}"; $ed "$CONF"
}

cmd_preview() {
  local kv sets=(); for kv in "$@"; do [[ $kv == *=* ]] && sets+=(--set "$kv"); done
  "$ENGINE" ${sets[@]+"${sets[@]}"} preview 20
}

cmd_installer() { # uninstall | restore
  local what=$1; shift
  if [[ -x $DATA_DIR/install.sh ]]; then exec "$DATA_DIR/install.sh" "$what" "$@"
  else die "installer copy not found; run  ./install.sh $what  from the termfx folder"; fi
}
