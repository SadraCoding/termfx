#!/usr/bin/env bash
# build.sh - turn the source tree into ONE self-contained installer: dist/termfx-install.sh
set -euo pipefail
cd "$(dirname "$0")"
OUT=dist/termfx-install.sh
MARK=__TERMFX_EMBED_EOF__
FILES=(src/termfx-engine src/termfx src/init.zsh src/init.bash src/config.default
       engine_bundle
       src/termfx.d/settings.sh src/termfx.d/art.sh src/termfx.d/status.sh
       src/art/girl.txt src/art/arch.txt src/art/tux.txt src/art/blocks.txt src/art/spinner.txt
       gen/themes.py lib/rcpatch.py)
ENGINE_FILES=(src/termfx_engine/__init__.py src/termfx_engine/__main__.py
              src/termfx_engine/_shared.py src/termfx_engine/_system.py
              src/termfx_engine/_color.py src/termfx_engine/_art.py
              src/termfx_engine/_info.py src/termfx_engine/_layout.py
              src/termfx_engine/_effects.py src/termfx_engine/_render.py
              src/termfx_engine/_commands.py)

for f in "${FILES[@]}"; do
  [[ $f == engine_bundle ]] && continue
  [[ -f $f ]] || { echo "missing $f" >&2; exit 1; }
  if grep -qx "$MARK" "$f"; then echo "$f contains the embed marker" >&2; exit 1; fi
done
for f in "${ENGINE_FILES[@]}"; do
  [[ -f $f ]] || { echo "missing $f" >&2; exit 1; }
  if grep -qx "$MARK" "$f"; then echo "$f contains the embed marker" >&2; exit 1; fi
done

mkdir -p dist
{
  while IFS= read -r line; do
    case $line in
      '#@DIST_FLAG') echo 'TERMFX_DIST=1' ;;
      '#@EMBED')
        for f in "${FILES[@]}"; do
          fn="__emb_${f//[^A-Za-z0-9]/_}"
          printf "%s() {\npython3 -c 'import base64,sys,zlib;sys.stdout.buffer.write(zlib.decompress(base64.b64decode(sys.stdin.buffer.read())))' <<'%s'\n" "$fn" "$MARK"
          if [[ $f == engine_bundle ]]; then
            python3 - "${ENGINE_FILES[@]}" <<'PY' | python3 -c 'import base64,sys,zlib;sys.stdout.write(base64.b64encode(zlib.compress(sys.stdin.buffer.read(),9)).decode())'
import sys,zipfile
with zipfile.ZipFile(sys.stdout.buffer,"w",compression=zipfile.ZIP_STORED) as z:
    for p in sys.argv[1:]: z.write(p,p.rsplit("/",1)[-1])
PY
          else
            python3 -c 'import base64,sys,zlib;sys.stdout.write(base64.b64encode(zlib.compress(sys.stdin.buffer.read(),9)).decode())' < "$f"
          fi
          printf '\n%s\n}\n' "$MARK"
        done ;;
      '. "$ROOT/lib/'*'.sh"')
        f=${line#'. "$ROOT/'}; f=${f%'"'}
        printf '# ---- %s ----\n' "$f"; cat "$f"; echo ;;
      *) printf '%s\n' "$line" ;;
    esac
  done < install.sh
} > "$OUT"
chmod +x "$OUT"
bash -n "$OUT"
echo "built $OUT ($(wc -l < "$OUT") lines)"
