cmd_art() {
  local sub=${1:-list}; shift || true
  case $sub in
    list)
      local cur; cur=$(cfg_get art); mkdir -p "$ART_DIR"
      shopt -s nullglob
      local i=0 f n
      say ""
      for f in "$ART_DIR"/*.txt; do
        n=${f##*/}; n=${n%.txt}; i=$((i+1))
        printf ' %s %s%3d)%s %-18s %s%5s lines  %s%s\n' "$([[ $n == "$cur" ]] && echo "${G}●${Z}" || echo ' ')" "$M" "$i" "$Z" "$n" "$D" "$(wc -l < "$f")" "$(du -h "$f" | cut -f1)" "$Z"
      done
      say ""
      say "${D}current: ${cur:-girl}   -   pick with: termfx art use NAME  (or its number, or random)${Z}" ;;
    add|paste)
      local n=${1:?usage: termfx art add NAME [FILE|URL|-] [-u]} src="" use=0; shift
      for a in "$@"; do case $a in -u|--use) use=1;; *) src=$a;; esac; done
      local f; f=$(art_file "$n"); mkdir -p "$ART_DIR"
      if [[ -z $src || $src == - ]]; then
        if [[ -t 0 ]]; then
          say "${B}Paste your ASCII art now.${Z} ${D}Finish with Ctrl-D on an empty line. (Huge art? use: termfx art edit $n)${Z}"
        fi
        cat > "$f"
      elif [[ $src =~ ^https?:// ]]; then fetch "$src" > "$f" || die "download failed"
      else [[ -f $src ]] || die "no such file: $src"; cp -- "$src" "$f"; fi
      finish_art "$f" "$n" "$use" ;;
    edit)
      local n=${1:?usage: termfx art edit NAME} f; f=$(art_file "$n"); mkdir -p "$ART_DIR"; touch "$f"
      local ed="${VISUAL:-${EDITOR:-}}"
      [[ -n $ed ]] || for e in nano micro vim vi; do have "$e" && { ed=$e; break; }; done
      [[ -n $ed ]] || die "no editor found, set \$EDITOR"
      "$ed" "$f"; finish_art "$f" "$n" 0
      say "use it with: termfx art use $n" ;;
    use)
      local n=${1:?usage: termfx art use NAME}
      if [[ $n =~ ^[0-9]+$ ]]; then local nn; nn=$(ls "$ART_DIR"/*.txt 2>/dev/null | sed -n "${n}p"); [[ -n $nn ]] || die "no art number $n (termfx art list)"; n=${nn##*/}; n=${n%.txt}; fi
      [[ $n == random || -f $n || -f $(art_file "$n") ]] || die "unknown art '$n' (termfx art list)"
      cfg_set art "$n"; "$ENGINE" prepare 2>/dev/null; ok "art = $n"; reload ;;
    show) cat -- "$(art_file "${1:?name}")" ;;
    rm|remove|delete)
      local n=${1:?name} f cur next=girl alt an
      f=$(art_file "$n"); [[ -f $f ]] || die "not found"
      cur=$(cfg_get art)
      if [[ $cur == "$n" ]]; then
        shopt -s nullglob
        for alt in "$ART_DIR"/*.txt; do
          an=${alt##*/}; an=${an%.txt}
          [[ $an != "$n" ]] && { next=$an; break; }
        done
        shopt -u nullglob
        warn "'$n' is your active art - switching to '$next' so the header keeps working"
        cfg_set art "$next"
        "$ENGINE" prepare 2>/dev/null || true
      fi
      rm -f -- "$f"; ok "removed '$n'"; reload ;;
    image)
      local n=${1:?usage: termfx art image NAME FILE|URL [WIDTH]} src=${2:?file or url} w=${3:-80} f tmp=""
      f=$(art_file "$n"); mkdir -p "$ART_DIR"
      if [[ $src =~ ^https?:// ]]; then tmp=$(mktemp); fetch "$src" > "$tmp" || die "download failed"; src=$tmp; fi
      if have chafa; then chafa --format symbols --symbols braille --colors none --size "${w}x$((w/2))" --animate off "$src" > "$f"
      elif have jp2a; then jp2a --width="$w" "$src" > "$f"
      else die "install chafa (recommended) or jp2a first"; fi
      [[ -n $tmp ]] && rm -f "$tmp"
      sed -i 's/\x1b\[[0-9;?]*[A-Za-z]//g' "$f"; finish_art "$f" "$n" 0 ;;
    text)
      local n=${1:?usage: termfx art text NAME "TEXT" [font]} t=${2:?text} font=${3:-} f; f=$(art_file "$n"); mkdir -p "$ART_DIR"
      if have figlet; then figlet ${font:+-f "$font"} -- "$t" > "$f"
      elif have toilet; then toilet ${font:+-f "$font"} -- "$t" > "$f"
      else die "install figlet or toilet first"; fi
      finish_art "$f" "$n" 0 ;;
    distro)
      local n=distro f; f=$(art_file "$n"); mkdir -p "$ART_DIR"
      "$ENGINE" distro-logo "${1:-}" > "$f" 2>/dev/null || { rm -f "$f"; die "could not extract a logo (needs fastfetch); paste your own: termfx art add NAME"; }
      finish_art "$f" "$n" 1 ;;
    info) "$ENGINE" art-info "${1:-}" ;;
    *) die "unknown: termfx art $sub  (try: termfx --help)" ;;
  esac
}

