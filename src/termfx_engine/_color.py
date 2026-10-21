from ._shared import (
    PALETTES, os, re,
)

def hex_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def palette_stops(name):
    n = (name or "").strip()
    if n.lower() in PALETTES:
        return PALETTES[n.lower()].split()
    if "," in n or n.startswith("#"):
        stops = [s for s in re.split(r"[,\s]+", n) if s]
        try:
            for s in stops:
                hex_rgb(s)
            if len(stops) == 1:
                stops = stops * 2
            return stops
        except Exception:
            pass
    return PALETTES["catppuccin"].split()

def build_lut(stops, n=256):
    pts = [hex_rgb(s) for s in stops]
    out = []
    for i in range(n):
        x = i / (n - 1) * (len(pts) - 1)
        a = int(x)
        if a >= len(pts) - 1:
            out.append(pts[-1])
            continue
        f = x - a
        p, q = pts[a], pts[a + 1]
        out.append(tuple(int(p[k] + (q[k] - p[k]) * f) for k in range(3)))
    return out

def to256(r, g, b):
    if abs(r - g) < 10 and abs(g - b) < 10:
        gray = (r + g + b) // 3
        if gray < 8:
            return 16
        if gray > 248:
            return 231
        return 232 + (gray - 8) * 24 // 247
    return 16 + 36 * int(r / 255 * 5 + 0.5) + 6 * int(g / 255 * 5 + 0.5) + int(b / 255 * 5 + 0.5)

def truecolor_on(cfg):
    v = cfg.get("truecolor", "auto").lower()
    if v in ("true", "1", "yes", "on"):
        return True
    if v in ("false", "0", "no", "off"):
        return False
    ct = os.environ.get("COLORTERM", "").lower()
    return ct in ("truecolor", "24bit") or "direct" in os.environ.get("TERM", "")
