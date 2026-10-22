"""Layout regression test: art + info panel must never overlap, art is never cut off or damaged.

Renders the header for many art files (braille, text, CJK, emoji, huge, tiny, multi-frame, ragged...),
terminal sizes, alignments and info panel sizes into a tiny terminal emulator and checks every cell.
Run:  python3 tests/layout_test.py [-v]
"""
import os, sys, re, tempfile, unicodedata, shutil, glob, collections
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, SRC)
tmp = tempfile.mkdtemp()
os.environ.update(XDG_CACHE_HOME=tmp+"/cache", XDG_CONFIG_HOME=tmp+"/conf", LANG="en_US.UTF-8", COLORTERM="truecolor")
os.makedirs(tmp+"/conf/termfx/art", exist_ok=True)
import termfx_engine._shared as S
from termfx_engine._system import load_config
from termfx_engine._layout import build_layout
from termfx_engine._render import Renderer
from termfx_engine._art import visible_width, parse_art, resolve_art, art_dims

def w(name, text): open(f"{tmp}/conf/termfx/art/{name}.txt","w",encoding="utf-8").write(text)
for p in glob.glob(SRC+"/art/*.txt"): shutil.copy(p, tmp+"/conf/termfx/art/")
w("big_braille", "\n".join("".join(chr(0x2800 + ((x*7+y*13) % 256)) for x in range(120)) for y in range(60)))
w("wide300", "\n".join("#"*300 for _ in range(12)))
w("tall90", "\n".join("|%s|" % ("-"*10) for _ in range(90)))
w("ascii140x50", "\n".join(("/\\_"*60)[i%3:][:140] for i in range(50)))
w("cjk", "\n".join("日本語のアート"*8 for _ in range(30)))
w("colored", "\n".join("\x1b[31m"+"@@##**"*30+"\x1b[0m" for _ in range(40)))
w("tabs", "\n".join("\t\t/\\\n\t/  \\" for _ in range(3)))
w("tiny", "^_^")
w("empty", "\n\n   \n")
w("tri40", "\n".join(" "*i + "x"*(i+1) for i in range(40)))
w("ragged", "\n".join("*"*((i*37)%90+1) for i in range(35)))
w("emoji", "\n".join("😀🚀✨"*10 for _ in range(10)))
w("frames_big", ("\n".join("@"*100 for _ in range(30)) + "\n---FRAME---\n" + "\n".join("#"*100 for _ in range(30))))
w("onecol", "\n".join("|" for _ in range(60)))

class Term:
    def __init__(s, cols, rows): s.cols, s.rows = cols, rows; s.g = {}; s.wr = collections.Counter(); s.r = s.c = 0; s.saved=(0,0)
    def feed(s, data):
        i = 0; n = len(data)
        while i < n:
            ch = data[i]
            if ch == "\x1b":
                if i+1 < n and data[i+1] == "7": s.saved=(s.r,s.c); i += 2; continue
                if i+1 < n and data[i+1] == "8": s.r,s.c = s.saved; i += 2; continue
                m = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])").match(data, i)
                if not m: i += 1; continue
                a, f = m.group(1), m.group(2); i = m.end()
                if f == "H":
                    p = (a.split(";") + ["1","1"])[:2]; s.r = int(p[0] or 1)-1; s.c = int(p[1] or 1)-1
                elif f == "K":
                    for k in [k for k in s.g if k[0]==s.r and k[1]>=s.c]: del s.g[k]
                elif f == "J": s.g.clear()
                continue
            cw = 2 if unicodedata.east_asian_width(ch) in ("W","F") else (0 if unicodedata.combining(ch) else 1)
            if cw and s.c + cw <= s.cols:
                if ch != " ":
                    s.wr[(s.r, s.c)] += 1
                s.g[(s.r, s.c)] = ch
                if cw == 2: s.g[(s.r, s.c+1)] = ""
            elif cw and ch != " ": s.wr[("OFF", s.r, s.c)] += 1
            s.c += cw; i += 1

def run(cols, rows, art, align, info_w, info_h=14):
    S.OVERRIDES.clear()
    ov = {"art": art, "align": align, "min_cols": "10", "min_rows": "5", "info": "builtin", "reserve":"10"}
    if info_w:
        ov["info"] = "auto"
        ov["info_cmd"] = "python3 -c \"[print('\\x1b[31m'+ 'k'*%d + '\\x1b[0m') for _ in range(%d)]\"" % (info_w, info_h)
    S.OVERRIDES.update(ov)
    shutil.rmtree(tmp+"/cache", ignore_errors=True)
    cfg = load_config()
    return cfg, build_layout(cfg, cols, rows, force=True)

def check(cols, rows, art, align, info_w, info_h=14):
    cfg, L = run(cols, rows, art, align, info_w, info_h)
    probs = []
    r = Renderer(cfg, L)
    t = Term(cols, rows)
    t.feed(r.render(5.0, top=0, save=False))
    for k, v in t.wr.items():
        if k[0] == "OFF": probs.append("off-screen write"); break
        if v > 1: probs.append("OVERLAP double write @%s" % (k,)); break
    # art complete & intact
    fr = L.frames[int(5.0*1000/r.frame_ms) % len(L.frames)] if len(L.frames) > 1 else L.frames[0]
    miss = 0; tot = 0
    for y, row in enumerate(fr):
        for x, ch in enumerate(row):
            if ch in (" ", ""): continue
            tot += 1
            if t.g.get((L.art_y + y, L.art_x + x)) != ch: miss += 1
    if miss: probs.append("art damaged %d/%d" % (miss, tot))
    if L.art_x + L.aw > cols: probs.append("art beyond right edge")
    if L.art_y + L.ah > L.H: probs.append("art taller than header")
    cap = max(6, rows - 10)
    if L.H > cap and L.mode != "art": probs.append("H %d > cap %d" % (L.H, cap))
    if L.H > rows: probs.append("H > rows")
    # info: every printed row must start where promised and end inside the screen
    if L.info:
        for i, l in enumerate(L.info[:L.H - L.info_y]):
            if not any(k[0] == L.info_y + i for k in t.g if k[1] >= L.info_x) and visible_width(l) > 0: probs.append("info row missing"); break
        if L.info_x + L.info_w > cols: probs.append("info beyond edge")
        # art box and info must not share columns on the same rows
        art_rows = set(range(L.art_y, L.art_y + L.ah)); info_rows = set(range(L.info_y, L.info_y + len(L.info[:L.H-L.info_y])))
        if art_rows & info_rows and not (L.art_x + L.aw <= L.info_x): probs.append("art/info columns collide")
    # aspect (only when scaled)
    p = resolve_art(art)
    src = parse_art(open(p, encoding="utf-8", errors="replace").read()) if p else []
    if src and L.scale < 1.0 and (art not in ("wide300", "tall90", "onecol")):
        sw, sh = art_dims(src)
        if abs((L.aw/L.ah)/(sw/sh) - 1) > 0.45: probs.append("aspect %.2f->%.2f" % (sw/sh, L.aw/L.ah))
    return probs, L

ARTS = ["girl","arch","blocks","tux","spinner","big_braille","wide300","tall90","ascii140x50","cjk","colored","tabs","tiny","tri40","ragged","emoji","frames_big","onecol","empty"]
if __name__ == "__main__":
    tot = bad = 0; kinds = collections.Counter(); modes = collections.Counter()
    for cols, rows in [(80,24),(90,30),(100,30),(120,40),(160,50),(200,60),(60,20)]:
        for art in ARTS:
            for align in ("left","center","right"):
                for iw, ih in ((0,14),(45,14),(70,14),(120,14),(50,40)):
                    tot += 1
                    try: probs, L = check(cols, rows, art, align, iw, ih)
                    except Exception as e:
                        import traceback; probs = ["EXC "+repr(e)]; L=None
                        if "-t" in sys.argv: traceback.print_exc()
                    if L is not None: modes[L.mode] += 1
                    if probs:
                        bad += 1
                        for p in probs: kinds[p.split()[0]+" "+(p.split()[1] if len(p.split())>1 else "")] += 1
                        if "-v" in sys.argv: print(cols, rows, art, align, iw, ih, probs, (L.mode, L.aw, L.ah, L.H, L.info_x) if L else "")
    print("layout test: %d cases, %d problems %s  arrangements: %s" % (tot, bad, dict(kinds), dict(modes)))
    sys.exit(1 if bad else 0)
