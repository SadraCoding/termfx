from ._shared import (
    ANSI_RE, ART_DIR, CACHE_DIR, CSI_ANY, FALLBACK_ART,
    FRAME_RE, OSC_RE, glob, hashlib, json,
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

def scale_rows(rows, H0, W0, nh, nw):
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
            if cand and avg >= 0.09:
                tgt = min(1.0, avg * 1.6)
                line.append(min(cand, key=lambda p: abs(p[0] - tgt))[1])
            else:
                line.append(" ")
        out.append(line)
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
    H0 = max(len(f) for f in frames)
    W0 = max(len(r) for f in frames for r in f)
    if H0 <= th and W0 <= tw:
        return frames
    if mode in ("auto", "scale"):
        s = max(H0 / th, W0 / tw)
        nh = max(1, min(th, int(H0 / s + 0.5)))
        nw = max(1, min(tw, int(W0 / s + 0.5)))
        frames = [scale_rows(f, H0, W0, nh, nw) for f in frames]
    return [crop_rows(f, tw, th, crop) for f in frames]

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

def load_art_frames(cfg, tw, th):
    path = resolve_art(cfg["art"])
    if not path:
        return [[cellify(l) for l in FALLBACK_ART]], None
    try:
        st = os.stat(path)
        key = "%s|%s|%s|%d|%d|%s|%s|v2" % (os.path.realpath(path), st.st_mtime_ns, st.st_size,
                                          tw, th, cfg["fit"], cfg["crop"])
        cp = os.path.join(CACHE_DIR, "art-" + hashlib.sha1(key.encode()).hexdigest()[:20] + ".json")
        try:
            with open(cp, encoding="utf-8") as fh:
                frames = json.load(fh)
            if frames:
                return frames, path
        except Exception:
            pass
        with open(path, encoding="utf-8", errors="replace") as fh:
            frames = parse_art(fh.read())
        if not frames:
            return [[cellify(l) for l in FALLBACK_ART]], path
        frames = fit_frames(frames, tw, th, cfg["fit"].lower(), cfg["crop"].lower())
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp = cp + ".%d" % os.getpid()
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(frames, fh, ensure_ascii=False)
            os.replace(tmp, cp)
        except Exception:
            pass
        return frames, path
    except Exception:
        log_error()
        return [[cellify(l) for l in FALLBACK_ART]], path

def keep_sgr(s):
    s = OSC_RE.sub("", s)
    s = CSI_ANY.sub(lambda m: m.group(0) if m.group(0).endswith("m") else "", s)
    return re.sub(r"[\x00-\x08\x0b-\x1a\x1c-\x1f\x7f]", "", s)

def clip_ansi(s, n):
    out, vis = [], 0
    for part in re.split(r"(\x1b\[[0-9;:]*m)", s):
        if part.startswith("\x1b["):
            out.append(part)
            continue
        for ch in part:
            if unicodedata.combining(ch):
                out.append(ch)
                continue
            w = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
            if vis + w > n:
                return "".join(out) + "\x1b[0m"
            out.append(ch)
            vis += w
    return "".join(out)
