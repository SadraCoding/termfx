import os, re, shutil, sys, time
path, mode, init, keep = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "1"
BEGIN, END = "# >>> termfx >>>", "# <<< termfx <<<"
try:
    orig = open(path, encoding="utf-8").read()
except FileNotFoundError:
    orig = ""
txt = re.sub(r"\n?" + re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", "\n", orig, flags=re.S)
if mode in ("install", "clean"):
    txt = re.sub(r"(?ms)^\n?# animated arch logo\n.*?^fi\n", "\n", txt)
    txt = re.sub(r"(?m)^\n?# terminal ui\n(?:(?:alias |export |\[\[ -f /usr/share/fzf).*\n)+", "\n", txt)
    txt = re.sub(r'(?m)^[ \t]*eval "\$\(starship init (?:zsh|bash)\)"[ \t]*\n', "", txt)
    if not keep:
        txt = re.sub(r"(?m)^([ \t]*)((?:command[ \t]+)?(?:fastfetch|neofetch|pfetch|macchina|screenfetch|onefetch|nerdfetch)\b.*)$",
                     r"\1: # [termfx] \2", txt)
if mode == "install":
    txt = txt.rstrip("\n") + ("\n" if txt.strip() else "") + "\n%s\n[ -r \"%s\" ] && . \"%s\"\n%s\n" % (BEGIN, init, init, END)
elif mode == "uninstall":
    txt = re.sub(r"(?m)^([ \t]*): # \[termfx\] ", r"\1", txt)
    txt = txt.rstrip("\n") + ("\n" if txt.strip() else "")
if txt != orig:
    if orig:
        shutil.copy2(path, path + ".termfx-" + time.strftime("%Y%m%d-%H%M%S") + ".bak")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(txt)
    print("patched")
else:
    print("unchanged")
