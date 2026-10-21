#!/usr/bin/env bash
# tests/smoke.sh [path/to/install.sh]  - install into a throw-away HOME, check reset + restore
set -uo pipefail
cd "$(dirname "$0")/.."
INSTALLER=${1:-./install.sh}
INSTALLER=$(readlink -f "$INSTALLER")
H=$(mktemp -d); trap 'rm -rf "$H"' EXIT
fail=0
check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
export HOME="$H" SHELL=/bin/bash TERM=xterm-256color XDG_CONFIG_HOME= XDG_DATA_HOME= XDG_CACHE_HOME=
unset XDG_CONFIG_HOME XDG_DATA_HOME XDG_CACHE_HOME ZDOTDIR DISPLAY WAYLAND_DISPLAY

# ---- a "messy" pre-existing setup
mkdir -p "$H/.oh-my-zsh" "$H/.config/ghostty" "$H/.config/fastfetch"
echo 'export ZSH=$HOME/.oh-my-zsh; ZSH_THEME=agnoster; plugins=(git)' > "$H/.zshrc"
echo 'alias gs="git status"; eval "$(starship init bash)"; neofetch' > "$H/.bashrc"
echo 'theme = old' > "$H/.config/ghostty/config"
echo 'format = "$all"' > "$H/.config/starship.toml"
echo 'old p10k' > "$H/.p10k.zsh"
cp "$H/.bashrc" "$H/bashrc.orig"; cp "$H/.zshrc" "$H/zshrc.orig"

echo "== install ($INSTALLER)"
sh "$INSTALLER" -y --no-packages --no-font --shell both >"$H/install.log" 2>&1 || { cat "$H/install.log"; fail=1; }
check "engine installed"              '[[ -x $H/.local/bin/termfx-engine ]]'
check "cli installed"                 '[[ -x $H/.local/bin/termfx ]]'
check "5 art files"                   '[[ $(ls $H/.config/termfx/art/*.txt | wc -l) -eq 5 ]]'
check "config written"                '[[ -f $H/.config/termfx/config ]]'
check "starship theme generated"      '[[ -s $H/.config/termfx/starship.toml ]]'
check "plain starship theme generated" '[[ -s $H/.config/termfx/starship-plain.toml ]]'
check "starship themes are valid TOML" 'python3 - "$H/.config/termfx" <<PY
import sys
try:
    import tomllib
except ImportError:
    sys.exit(0)
for n in ("starship.toml", "starship-plain.toml"):
    tomllib.load(open(sys.argv[1] + "/" + n, "rb"))
PY'
check "fastfetch theme generated"     '[[ -s $H/.config/termfx/fastfetch.jsonc ]]'
check "zshrc has termfx block"        'grep -q ">>> termfx >>>" $H/.zshrc'
check "bashrc has termfx block"       'grep -q ">>> termfx >>>" $H/.bashrc'
check "oh-my-zsh moved out"           '[[ ! -e $H/.oh-my-zsh ]]'
check "old starship.toml moved out"   '[[ ! -e $H/.config/starship.toml ]]'
check "old ghostty config moved out"  '! grep -q "theme = old" $H/.config/ghostty/config 2>/dev/null'
check "old alias gone from bashrc"    '! grep -q "gs=" $H/.bashrc'
check "backup + manifest exist"       '[[ -s $H/.termfx-backup/latest/MANIFEST ]]'
WANT=$(sed -n 's/^VERSION="\(.*\)"/\1/p' install.sh | head -n1)
check "engine version = installer ($WANT)" '[[ $($H/.local/bin/termfx-engine version) == $WANT ]]'
check "no hold setting left"          '! grep -q "^hold" $H/.config/termfx/config'
check "no comment junk in pause list"  '! $H/.local/bin/termfx-engine height | grep -q "extra,commands"'
check "engine doctor runs"            '$H/.local/bin/termfx-engine doctor >/dev/null 2>&1'
check "art-info works"                '$H/.local/bin/termfx-engine art-info girl >/dev/null 2>&1'
check "spinner has 2 different frames" '[[ $(sed -n "1,/---FRAME---/p" $H/.config/termfx/art/spinner.txt | md5sum) != $(sed -n "/---FRAME---/,\$p" $H/.config/termfx/art/spinner.txt | tail -n +2 | md5sum) ]]'
if command -v zsh >/dev/null; then check "zsh init parses" 'zsh -n $H/.config/termfx/init.zsh'; fi
check "bash init parses"              'bash -n $H/.config/termfx/init.bash'
check "bash starts clean w/ header disabled" 'TERMFX_DISABLE=1 bash -ic "exit" >/dev/null 2>&1'

echo "== cli regressions"
export PATH="$H/.local/bin:$PATH"
check "custom #hex palette survives"   'termfx palette "#ff0080,#00e5ff,#7a00ff" >/dev/null && [[ $(termfx get palette) == "#ff0080,#00e5ff,#7a00ff" ]] && [[ $(python3 -c "
import importlib.machinery as m, importlib.util as u
l=m.SourceFileLoader(\"e\",\"$H/.local/bin/termfx-engine\"); s=u.spec_from_loader(\"e\",l); x=u.module_from_spec(s); l.exec_module(x)
print(x.load_config()[\"palette\"])") == "#ff0080,#00e5ff,#7a00ff" ]]'
check "termfx effect fire works"       'termfx effect fire >/dev/null 2>&1 && [[ $(termfx get effect) == fire ]]'
check "unknown effect is rejected"     '! termfx effect nope >/dev/null 2>&1'
check "every theme exits 0"            '( for t in catppuccin tokyonight dracula nord gruvbox rosepine onedark mono; do termfx theme $t >/dev/null 2>&1 || exit 1; done )'
check "prompt_char with quote is valid TOML" 'termfx char "'"'"'" >/dev/null 2>&1 && python3 -c "
import sys
try: import tomllib
except ImportError: sys.exit(0)
tomllib.load(open(\"$H/.config/termfx/starship.toml\",\"rb\"))"'

echo "== idempotent re-install"
sh "$INSTALLER" -y --no-packages --no-font --shell both >"$H/install2.log" 2>&1 || { cat "$H/install2.log"; fail=1; }
check "exactly one block in bashrc"   '[[ $(grep -c ">>> termfx >>>" $H/.bashrc) -eq 1 ]]'

echo "== restore"
PATH="$H/.local/bin:$PATH" termfx restore "$H/.termfx-backup/original" >"$H/restore.log" 2>&1 || { cat "$H/restore.log"; fail=1; }
check "oh-my-zsh is back"             '[[ -d $H/.oh-my-zsh ]]'
check "old starship.toml is back"     'grep -q "\$all" $H/.config/starship.toml'
check "old ghostty config is back"    'grep -q "theme = old" $H/.config/ghostty/config'
check "p10k is back"                  '[[ -f $H/.p10k.zsh ]]'

echo "== uninstall"
sh "$INSTALLER" uninstall -y >"$H/un.log" 2>&1 || { cat "$H/un.log"; fail=1; }
check "binaries removed"              '[[ ! -e $H/.local/bin/termfx && ! -e $H/.local/bin/termfx-engine ]]'
check "no termfx block left in rc"    '! grep -qs ">>> termfx >>>" $H/.bashrc $H/.zshrc'
check "config kept (no --purge)"      '[[ -d $H/.config/termfx ]]'

((fail)) && { echo "SMOKE: FAILED"; exit 1; }
echo "SMOKE: PASSED"
