cfg_get() { # value of KEY: "quoted" values are kept whole (they may contain #), otherwise a trailing " # comment" is dropped
  local v
  v=$(sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$CONF" 2>/dev/null | tail -n1)
  case $v in
    \"*\"*) v=${v#\"}; v=${v%%\"*} ;;
    \'*\'*) v=${v#\'}; v=${v%%\'*} ;;
    *) v=$(sed 's/[[:space:]]\{1,\}#.*$//; s/[[:space:]]*$//' <<<"$v") ;;
  esac
  printf '%s\n' "$v"
}
cfg_set() {
  local k=$1 v=$2 tmp
  # a value containing '#' must be quoted, or it would be read back as a comment
  case $v in \"*\"|\'*\') ;; *\#*) v="\"$v\"" ;; esac
  mkdir -p "$CONF_DIR"; touch "$CONF"
  tmp=$(mktemp "$CONF_DIR/.cfg.XXXXXX")
  K="$k" V="$v" awk 'BEGIN{d=0; k=ENVIRON["K"]; v=ENVIRON["V"]} { if ($0 ~ "^[ \t]*" k "[ \t]*=") { if(!d){print k " = " v; d=1}; next } print } END{ if(!d) print k " = " v }' "$CONF" > "$tmp" && mv "$tmp" "$CONF" || { rm -f "$tmp"; return 1; }
}

reload() {
  local f="${TERMFX_FLAG:-}" p h par
  if [[ -n $f && -r $f.state ]]; then
    read -r p h par < "$f.state" || true
    if [[ -n ${p:-} ]] && kill -USR1 "$p" 2>/dev/null; then ok "applied live (press Enter if the prompt looks shifted)"; return; fi
  fi
  say "${D}saved - will apply in new terminals (or run: exec \$SHELL)${Z}"
}

regen() { have python3 || die "python3 needed"; CONF_DIR="$CONF_DIR" python3 "$THEMES" || die "theme generator failed"; reload; }
cmd_fastfetch() {
  local choice=${1:-}
  local cur; cur=$(cfg_get fetch_preset)
  # -- list available presets (from the theme generator)
  if [[ $choice == list || -z $choice && ! -t 0 ]]; then
    say "${B}Fastfetch panel presets${Z}  ${D}(current: ${cur:-none — custom})${Z}"
    while IFS= read -r line; do
      local pname; pname=${line%% *}
      if [[ $pname == "$cur" ]]; then
        printf "  ${G}●${Z} %s\n" "$line"
      else
        printf '    %s\n' "$line"
      fi
    done < <(CONF_DIR="$CONF_DIR" python3 "$THEMES" --list fetch 2>/dev/null)
    say ""
    say "${D}usage: termfx fastfetch NAME   or: termfx fastfetch preview NAME${Z}"
    return
  fi
  # -- interactive picker
  if [[ -z $choice ]]; then
    say "${B}Fastfetch panel presets:${Z}"
    local -a names descs
    while IFS= read -r line; do
      names+=("${line%% *}")
      descs+=("${line#* }")
    done < <(CONF_DIR="$CONF_DIR" python3 "$THEMES" --list fetch 2>/dev/null)
    local i=1
    for idx in "${!names[@]}"; do
      printf '  %2d) %-13s %s\n' "$i" "${names[$idx]}" "${descs[$idx]}"
      ((i++))
    done
    printf "\n  ${D}q) cancel${Z}\n"
    read -r -p "Choose 1-${#names[@]} (or preset name): " choice || return 1
    [[ $choice == q || $choice == Q ]] && return 0
    if [[ $choice =~ ^[0-9]+$ ]]; then
      (( choice >= 1 && choice <= ${#names[@]} )) || die "out of range"
      choice="${names[$((choice-1))]}"
    fi
  fi
  # -- validate preset name
  local valid; valid=$(CONF_DIR="$CONF_DIR" python3 "$THEMES" --list fetch 2>/dev/null | awk '{print $1}')
  grep -qx -- "$choice" <<<"$valid" || die "unknown preset '$choice'  (termfx fastfetch list)"
  # -- apply
  cfg_set fetch_preset "$choice"
  cfg_set info fastfetch; cfg_set info_config auto; cfg_set info_cmd ""
  cfg_set info_rows ""    # let the preset define the rows
  rm -f "$CACHE_DIR/info.json" 2>/dev/null
  ok "fastfetch preset = $choice"
  regen
}
choose() { # KEY NAME LISTCMD...
  local k=$1 n=$2; shift 2
  if [[ $n == list || -z $n ]]; then "$@" | sed "s/^/   /"; say "${D}current: $(cfg_get "$k")${Z}"; return; fi
  local all; all=$("$@" | awk '{print $1}'); grep -qx -- "$n" <<<"$all" || die "unknown '$n' (try: list)"
  cfg_set "$k" "$n"; ok "$k = $n"; regen
}

STARSHIP_MODULE_NAMES="username hostname localip shlvl singularity kubernetes nats directory vcsh fossil_branch fossil_metrics git_branch git_commit git_state git_metrics git_status hg_branch hg_state pijul_channel docker_context package bun c cmake cobol cpp daml dart deno dotnet elixir elm erlang fennel fortran gleam golang gradle haskell haxe helm java julia kotlin lua maven mojo nim nodejs ocaml odin opa perl php pulumi purescript python quarto raku rlang red ruby rust scala solidity swift terraform typst vlang vagrant xmake zig buf guix_shell nix_shell conda pixi meson spack memory_usage aws gcloud openstack azure direnv env_var mise crystal sudo cmd_duration line_break jobs battery time status container netns os shell"
STARSHIP_DEFAULT_MODULES="os username hostname directory git_branch git_status python nodejs rust golang java docker_context cmd_duration status time"
cmd_starship() {
  local sub=${1:-list}; shift || true
  case $sub in
    list|show)
      local k value; for k in newline right_prompt follow_symlinks scan_timeout command_timeout directory_length truncate_to_repo git_branch_length git_remote username_always ssh_only duration_min time_format fill_symbol git_symbol git_conflicted git_ahead git_behind git_diverged git_untracked git_stashed git_modified git_staged git_renamed git_deleted; do
        value=$(cfg_get "starship_$k")
        case $k in
          newline) value=${value:-true} ;; follow_symlinks) value=${value:-true} ;;
          right_prompt|git_remote) value=${value:-false} ;;
          scan_timeout) value=${value:-30} ;; command_timeout) value=${value:-500} ;;
          directory_length) value=${value:-3} ;; truncate_to_repo) value=${value:-true} ;;
          git_branch_length) value=${value:-0} ;; username_always) value=${value:-true} ;;
          ssh_only) value=${value:-true} ;; duration_min) value=${value:-2000} ;;
          time_format) value=${value:-%H:%M} ;; fill_symbol) value=${value:-·} ;;
          git_symbol) value=${value:-} ;; git_conflicted) value=${value:-⚡} ;;
          git_ahead) value=${value:-⇡\${count\}} ;; git_behind) value=${value:-⇣\${count\}} ;;
          git_diverged) value=${value:-⇕⇡\${ahead_count\}⇣\${behind_count\}} ;;
          git_untracked) value=${value:-?\${count\}} ;; git_stashed) value=${value:-≡} ;;
          git_modified) value=${value:-!\${count\}} ;; git_staged) value=${value:-+\${count\}} ;;
          git_renamed) value=${value:-»} ;; git_deleted) value=${value:-✘\${count\}} ;;
        esac
        printf '  %-24s %s\n' "$k" "$value"
      done
      local active_theme; active_theme=$(cfg_get starship_theme); say "  theme: ${active_theme:-terminal-match}"
      local mods; mods=$(cfg_get starship_modules)
      say "  modules: ${mods:-$STARSHIP_DEFAULT_MODULES}"
      say "  themes: $(CONF_DIR="$CONF_DIR" python3 "$THEMES" --list starship 2>/dev/null | awk '{printf "%s%s", sep, $1; sep=" "}')"
      say "  presets: balanced minimal developer cloud server full"
      say "  module control: termfx starship module list|on NAME|off NAME"
      ;;
    set)
      local k=${1:?usage: termfx starship set OPTION VALUE} value; shift
      [[ $# -gt 0 ]] || die "usage: termfx starship set OPTION VALUE"
      value=$*
      case " $STARSHIP_KEYS " in *" starship_$k "*) ;; *) die "unknown Starship option '$k' (termfx starship list)" ;; esac
      k=${k#starship_}
      if [[ $k == theme ]]; then cmd_starship theme "$value"; return; fi
      case $k in
        newline|right_prompt|follow_symlinks|truncate_to_repo|git_remote|username_always|ssh_only)
          case ${value,,} in true|yes|on|1) value=true ;; false|no|off|0) value=false ;; *) die "$k expects true or false" ;; esac ;;
        scan_timeout|command_timeout|directory_length|git_branch_length|duration_min)
          [[ $value =~ ^[0-9]+$ ]] || die "$k expects a number"
          case $k in
            scan_timeout) ((value >= 1 && value <= 5000)) || die "scan_timeout range: 1..5000 ms" ;;
            command_timeout) ((value >= 1 && value <= 60000)) || die "command_timeout range: 1..60000 ms" ;;
            directory_length) ((value <= 20)) || die "directory_length range: 0..20" ;;
            git_branch_length) ((value <= 200)) || die "git_branch_length range: 0..200 (0 = unlimited)" ;;
            duration_min) ((value <= 600000)) || die "duration_min range: 0..600000 ms" ;;
          esac ;;
        *)
          [[ -n $value && $value != *$'\n'* && $value != *$'\r'* && $value != *\"* && $value != *\'* ]] || die "$k expects a non-empty single-line value without quotes" ;;
      esac
      if [[ $k == modules ]]; then
        if [[ $value != none ]]; then
          local m; for m in ${value//,/ }; do
            [[ " $STARSHIP_MODULE_NAMES " == *" $m "* ]] || die "unknown Starship module '$m' (termfx starship module list)"
          done
          value="${value//,/ }"
        fi
      fi
      cfg_set "starship_$k" "$value"; ok "starship $k = $value"; regen ;;
    theme)
      local name=${1:-list} valid modules current style
      valid=$(CONF_DIR="$CONF_DIR" python3 "$THEMES" --list starship 2>/dev/null)
      if [[ $name == list || -z $name ]]; then
        current=$(cfg_get starship_theme); current=${current:-terminal-match}
        say "Starship themes (current: $current):"
        while IFS= read -r line; do
          if [[ ${line%% *} == "$current" ]]; then printf '  %s●%s %s\n' "$G" "$Z" "$line"
          else printf '    %s\n' "$line"; fi
        done <<<"$valid"
        say "  generated files: $CONF_DIR/starship-themes/"
        return
      fi
      [[ $name =~ ^[a-z0-9-]+$ ]] && grep -q "^$name[[:space:]]" <<<"$valid" || die "unknown Starship theme '$name' (termfx starship theme list)"
      modules=$(CONF_DIR="$CONF_DIR" python3 "$THEMES" --starship-modules "$name") || die "could not load Starship theme '$name'"
      style=$(CONF_DIR="$CONF_DIR" python3 "$THEMES" --starship-style "$name") || die "could not load Starship theme '$name'"
      cfg_set starship_theme "$name"; cfg_set starship_modules "$modules"
      [[ -z $style ]] || cfg_set prompt_style "$style"
      regen; ok "Starship theme = $name" ;;
    module)
      local action=${1:-list} name=${2:-} current; current=$(cfg_get starship_modules)
      [[ -n $current ]] || current=$STARSHIP_DEFAULT_MODULES
      case $action in
        list|show)
          local m; for m in $STARSHIP_MODULE_NAMES; do
            if [[ " $current " == *" $m "* ]]; then printf '  %s %-18s enabled\n' "${G}●${Z}" "$m"
            else printf '  %s %-18s disabled\n' "${D}○${Z}" "$m"; fi
          done ;;
        on|enable|off|disable)
          [[ -n $name ]] || die "usage: termfx starship module $action NAME"
          [[ " $STARSHIP_MODULE_NAMES " == *" $name "* ]] || die "unknown module '$name' (termfx starship module list)"
          local -a selected=(); local found=0 m
          for m in ${current//,/ }; do
            [[ $m == "$name" ]] && { found=1; continue; }
            [[ " $STARSHIP_MODULE_NAMES " == *" $m "* ]] && selected+=("$m")
          done
          case $action in on|enable) ((found)) || selected+=("$name") ;; esac
          cfg_set starship_modules "${selected[*]:-none}"
          ok "starship module $name ${action/on/enabled}"; regen ;;
        *) die "usage: termfx starship module list|on NAME|off NAME" ;;
      esac ;;
    preset)
      local preset=${1:-list} modules
      case $preset in
        list) say "Starship presets: balanced minimal developer cloud server full"; return ;;
        balanced) modules=$STARSHIP_DEFAULT_MODULES ;;
        minimal) modules="username directory git_branch git_status cmd_duration status time" ;;
        developer) modules="$STARSHIP_DEFAULT_MODULES bun c cmake cpp dart deno dotnet elixir elm erlang gradle haskell julia kotlin lua perl php ruby scala swift package" ;;
        cloud) modules="$STARSHIP_DEFAULT_MODULES aws gcloud kubernetes terraform nix_shell" ;;
        server) modules="username hostname localip shlvl directory git_branch git_status docker_context aws azure gcloud kubernetes cmd_duration jobs sudo status time shell" ;;
        full) modules=$STARSHIP_MODULE_NAMES ;;
        *) die "unknown preset '$preset' (termfx starship preset list)" ;;
      esac
      cfg_set starship_modules "$modules"; ok "Starship preset = $preset"; regen ;;
    *) die "usage: termfx starship list|theme list|NAME|set OPTION VALUE|module list|on|off NAME|preset NAME" ;;
  esac
}

valid_name() { [[ $1 =~ ^[A-Za-z0-9._-]+$ ]] || die "bad name '$1' (letters, digits, . _ - only)"; }
art_file()   { valid_name "$1"; echo "$ART_DIR/${1%.txt}.txt"; }
fetch() {
  if have curl; then curl -fsSL --max-filesize 20000000 --connect-timeout 15 "$1"
  elif have wget; then wget -q -O - "$1"
  else die "need curl or wget"; fi
}
finish_art() { # file name use
  local f=$1 n=$2 use=$3
  [[ -s $f ]] || { rm -f "$f"; die "nothing saved (empty input)"; }
  ok "saved: $f ($(wc -l < "$f") lines)"
  "$ENGINE" art-info "$n" 2>/dev/null | sed 's/^/   /'
  if [[ $use == 1 ]]; then cfg_set art "$n"; "$ENGINE" prepare 2>/dev/null; ok "now using '$n'"; reload; fi
}

valid_palette() {
  local p=$1 all
  [[ $p == auto ]] && return 0
  if [[ $p == \#* || $p == *,* ]]; then
    # custom hex list - engine validates at runtime; do a light check here
    local s
    for s in ${p//,/ }; do
      s=${s#\#}
      [[ $s =~ ^[0-9A-Fa-f]{3}$ || $s =~ ^[0-9A-Fa-f]{6}$ ]] || die "bad colour in palette: '$s' (want #rgb or #rrggbb)"
    done
    return 0
  fi
  all=$("$ENGINE" list palettes 2>/dev/null)
  grep -qx -- "$p" <<<"$all" || die "unknown palette '$p' (termfx palette list)"
}
