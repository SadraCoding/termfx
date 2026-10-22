from ._shared import (
    ANSI_RE, ART_DIR, CACHE_DIR, CSI_ANY, FALLBACK_ART,
    FRAME_RE, OSC_RE, UTF8, glob, hashlib, json,
    os, random, re, unicodedata,
)
from ._system import (
    log_error,
)

_BLOCKS = {"█": 1.0, "▓": 0.75, "▒": 0.5, "░": 0.25, "▀": 0.5, "▄": 0.5, "▌": 0.5, "▐": 0.5,
           "■": 0.8, "●": 0.8, "◼": 0.8, "▪": 0.5}

_RAMP_STR = " .`'^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

_RAMP = {c: i / (len(_RAMP_STR) - 1) for i, c in enumerate(_RAMP_STR)}

def density(ch):
    if ch in (" ", ""):
        return 0.0
    o = ord(ch)
    if 0x2800 <= o <= 0x28FF:
        return bin(o - 0x2800).count("1") / 8.0
    d = _BLOCKS.get(ch)
    if d is not None:
        return d
    d = _RAMP.get(ch)
    return d if d is not None else 0.6

def cellify(line):
    out = []
    for ch in line:
        o = ord(ch)
        if o < 32 or o == 127 or o in (0x200B, 0x200C, 0x200D, 0xFE0F, 0xFEFF):
            continue
        if unicodedata.combining(ch):
            continue
        out.append(ch)
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            out.append("")
    return out

def parse_art(text):
    frames = [[]]
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if FRAME_RE.match(line):
            frames.append([])
            continue
        frames[-1].append(line)
    res = []
    for fr in frames:
        fr = [ANSI_RE.sub("", l).expandtabs(4).rstrip() for l in fr]
        while fr and not fr[0].strip():
            fr.pop(0)
        while fr and not fr[-1].strip():
            fr.pop()
        if not fr:
            continue
        res.append(fr)
    if not res:
        return []
    # one common indent for ALL frames; per-frame dedent makes animations jitter sideways
    ind = min(len(l) - len(l.lstrip(" ")) for fr in res for l in fr if l.strip())
    return [[cellify(l[ind:]) for l in fr] for fr in res]

def art_dims(frames):
    """(width, height) in terminal cells of the largest frame."""
    if not frames:
        return 0, 0
    return max(len(r) for f in frames for r in f), max(len(f) for f in frames)

def _narrow(rows):
    """Replace double-width glyphs by a narrow stand-in so scaling never splits a wide character."""
    out = []
    for r in rows:
        nr, prev_wide = [], False
        for ch in r:
            if ch == "":
                nr.append("#" if prev_wide else "")
                prev_wide = False
                continue
            wide = ch != " " and unicodedata.east_asian_width(ch) in ("W", "F")
            nr.append("#" if wide else ch)
            prev_wide = wide
        out.append(nr)
    return out

def scale_rows(rows, H0, W0, nh, nw):
    """Generic text art: area-average each block and pick the glyph with the closest ink density."""
    rows = _narrow(rows)
    out = []
    for ty in range(nh):
        y0 = ty * H0 // nh
        y1 = max(y0 + 1, (ty + 1) * H0 // nh)
        band = rows[y0:y1]
        line = []
        for tx in range(nw):
            x0 = tx * W0 // nw
            x1 = max(x0 + 1, (tx + 1) * W0 // nw)
            area = (y1 - y0) * (x1 - x0)
            tot = 0.0
            cand = []
            for rr in band:
                for ch in rr[x0:x1]:
                    d = density(ch)
                    if d > 0:
                        tot += d
                        cand.append((d, ch))
            avg = tot / area
            if cand and avg >= 0.06:
                tgt = min(1.0, avg * 1.6)
                line.append(min(cand, key=lambda p: abs(p[0] - tgt))[1])
            else:
                line.append(" ")
        out.append(line)
    return out

# ---- braille art is really a 2x4 dot bitmap: scale the bitmap, then re-encode it
_BR_BITS = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))
_BAYER4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))

def is_braille_art(frames):
    ink = br = 0
    for f in frames:
        for row in f:
            for ch in row:
                if ch in (" ", ""):
                    continue
                ink += 1
                if 0x2800 <= ord(ch) <= 0x28FF:
                    br += 1
    return ink > 0 and br / ink >= 0.8

def scale_braille(rows, H0, W0, nh, nw):
    Ws, Hs = W0 * 2, H0 * 4
    sat = [[0] * (Ws + 1) for _ in range(Hs + 1)]       # summed-area table of lit dots
    for y in range(Hs):
        row = rows[y // 4] if y // 4 < len(rows) else ()
        dy = y % 4
        acc = 0
        prev, cur = sat[y], sat[y + 1]
        for x in range(Ws):
            cx = x // 2
            ch = row[cx] if cx < len(row) else " "
            on = 0
            if ch not in (" ", ""):
                o = ord(ch)
                if 0x2800 <= o <= 0x28FF:
                    on = 1 if (o - 0x2800) & _BR_BITS[dy][x & 1] else 0
                else:
                    on = 1 if density(ch) >= 0.5 else 0
            acc += on
            cur[x + 1] = prev[x + 1] + acc
    Wd, Hd = nw * 2, nh * 4
    dots = [[0] * Wd for _ in range(Hd)]
    for ty in range(Hd):
        y0 = ty * Hs // Hd
        y1 = max(y0 + 1, (ty + 1) * Hs // Hd)
        for tx in range(Wd):
            x0 = tx * Ws // Wd
            x1 = max(x0 + 1, (tx + 1) * Ws // Wd)
            lit = sat[y1][x1] - sat[y0][x1] - sat[y1][x0] + sat[y0][x0]
            avg = lit / ((y1 - y0) * (x1 - x0))
            dots[ty][tx] = 1 if avg > (_BAYER4[ty & 3][tx & 3] + 0.5) / 16.0 else 0
    out = []
    for cy in range(nh):
        line = []
        for cx in range(nw):
            bits = 0
            for dy in range(4):
                for dx in range(2):
                    if dots[cy * 4 + dy][cx * 2 + dx]:
                        bits |= _BR_BITS[dy][dx]
            line.append(chr(0x2800 + bits) if bits else " ")
        out.append(line)
    return out

def trim_frames(frames):
    """Drop blank margins shared by all frames so the fitted art is as tight as possible."""
    if not frames:
        return frames
    top = min(next((i for i, r in enumerate(f) if any(c not in (" ", "") for c in r)), len(f)) for f in frames)
    bot = min(next((i for i, r in enumerate(reversed(f)) if any(c not in (" ", "") for c in r)), len(f)) for f in frames)
    frames = [f[top:len(f) - bot] for f in frames]
    if not all(frames):
        return frames
    left, right = 10 ** 9, 0
    for f in frames:
        for r in f:
            ink = [i for i, c in enumerate(r) if c not in (" ", "")]
            if ink:
                left, right = min(left, ink[0]), max(right, ink[-1] + 1)
    if right <= left:
        return frames
    out = []
    for f in frames:
        fr = []
        for r in f:
            r = r[left:right]
            while r and r[-1] in (" ",):
                r.pop()
            fr.append(r)
        out.append(fr)
    return out

def crop_rows(rows, tw, th, mode):
    if len(rows) > th:
        o = {"top": 0, "bottom": len(rows) - th}.get(mode, (len(rows) - th) // 2)
        rows = rows[o:o + th]
    out = []
    for r in rows:
        if len(r) > tw:
            o = 0 if mode in ("top",) else (len(r) - tw) // 2
            r = r[o:o + tw]
        out.append(r)
    return out

def fit_frames(frames, tw, th, mode, crop):
    """Make every frame fit inside tw x th cells.

    Art is ALWAYS scaled down as a whole (aspect ratio kept, never enlarged, never cut off).
    Only an explicit `fit = crop` in the config crops instead."""
    W0, H0 = art_dims(frames)
    if H0 <= th and W0 <= tw:
        return frames
    if mode == "crop":
        return [crop_rows(f, tw, th, crop) for f in frames]
    s = min(tw / W0, th / H0)
    nw = max(1, min(tw, int(W0 * s + 0.5)))
    nh = max(1, min(th, int(H0 * s + 0.5)))
    scaler = scale_braille if is_braille_art(frames) else scale_rows
    return trim_frames([scaler(f, H0, W0, nh, nw) for f in frames])

def resolve_art(name):
    name = (name or "girl").strip()
    if name == "random":
        files = sorted(glob.glob(os.path.join(ART_DIR, "*.txt")))
        if files:
            rnd = random.Random(os.environ.get("TERMFX_SEED") or None)
            return rnd.choice(files)
    n = os.path.expanduser(name)
    for c in (n, os.path.join(ART_DIR, n), os.path.join(ART_DIR, n + ".txt")):
        if os.path.isfile(c):
            return c
    return None

def load_art_source(cfg):
    """Parse the selected art file WITHOUT resizing it. Returns (frames, path)."""
    path = resolve_art(cfg["art"])
    fallback = [[cellify(l) for l in FALLBACK_ART]]
    if not path:
        return fallback, None
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            frames = parse_art(fh.read())
        return (frames or fallback), path
    except Exception:
        log_error()
        return fallback, path

def fit_art(cfg, frames, path, tw, th):
    """Fit parsed art into tw x th cells (result cached on disk, keyed by file + size)."""
    mode, crop = cfg["fit"].strip().lower(), cfg["crop"].strip().lower()
    W0, H0 = art_dims(frames)
    if H0 <= th and W0 <= tw:
        return frames
    cp = None
    if path:
        try:
            st = os.stat(path)
            key = "%s|%s|%s|%d|%d|%s|%s|v3" % (os.path.realpath(path), st.st_mtime_ns, st.st_size, tw, th, mode, crop)
            cp = os.path.join(CACHE_DIR, "art-" + hashlib.sha1(key.encode()).hexdigest()[:20] + ".json")
            with open(cp, encoding="utf-8") as fh:
                cached = json.load(fh)
            if cached:
                return cached
        except Exception:
            pass
    try:
        res = fit_frames(frames, tw, th, mode, crop)
    except Exception:
        log_error()
        res = fit_frames([[cellify(l) for l in FALLBACK_ART]], tw, th, "scale", crop)
    if cp:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp = cp + ".%d" % os.getpid()
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(res, fh, ensure_ascii=False)
            os.replace(tmp, cp)
        except Exception:
            pass
    return res

def load_art_frames(cfg, tw, th):
    frames, path = load_art_source(cfg)
    return fit_art(cfg, frames, path, tw, th), path

def keep_sgr(s):
    s = OSC_RE.sub("", s)
    s = CSI_ANY.sub(lambda m: m.group(0) if m.group(0).endswith("m") else "", s)
    return re.sub(r"[\x00-\x08\x0b-\x1a\x1c-\x1f\x7f]", "", s)

_SGR_SPLIT = re.compile(r"(\x1b\[[0-9;:]*m)")
_TRAIL = re.compile(r"[ \t]+((?:\x1b\[[0-9;:]*m)*)$")

def _cw(ch):
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1

def trim_trailing(s):
    """Remove trailing blanks that sit in front of the final colour codes."""
    return _TRAIL.sub(r"\1", s)

def visible_width(s):
    return sum(_cw(ch) for ch in _SGR_SPLIT.sub("", s))

def clip_ansi(s, n, ellipsis=True):
    """Cut a coloured string to n terminal cells; a cut line ends in an ellipsis so it never looks broken."""
    if n <= 0:
        return ""
    if visible_width(s) <= n:
        return s
    limit = n - 1 if ellipsis else n
    out, vis = [], 0
    for part in _SGR_SPLIT.split(s):
        if part.startswith("\x1b["):
            out.append(part)
            continue
        for ch in part:
            w = _cw(ch)
            if vis + w > limit:
                out.append("\x1b[0m")
                if ellipsis:
                    out.append("\u2026" if UTF8 else ">")
                return "".join(out)
            out.append(ch)
            vis += w
    return "".join(out)
