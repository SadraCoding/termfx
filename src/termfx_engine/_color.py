from ._shared import (
    PALETTES, os, re,
)

def hex_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

# plain colour names usable anywhere a palette is accepted:  termfx palette white
COLORS = {
    "white": "ffffff", "snow": "f5f5f5", "silver": "c0c0c0", "gray": "808080", "grey": "808080",
    "black": "101010", "red": "ff2d2d", "crimson": "dc143c", "orange": "ff8c00", "amber": "ffbf00",
    "yellow": "ffe600", "lime": "9dff00", "green": "22dd55", "mint-green": "3ddc97", "teal": "00b3a4",
    "cyan": "00e5ff", "sky-blue": "55b8ff", "blue": "2f6bff", "navy": "1a2a8a", "indigo": "4b3fd8",
    "purple": "9b4dff", "violet": "b57bff", "magenta": "ff2bd6", "pink": "ff7eb6", "hotpink": "ff3d9a",
    "brown": "a0623a", "beige": "e8d9b8",
}

def _color_hex(tok):
    t = tok.strip().lower()
    if t in COLORS:
        return COLORS[t]
    h = t.lstrip("#")
    if len(h) in (3, 6) and all(c in "0123456789abcdef" for c in h):
        return h
    return None

def palette_stops(name):
    n = (name or "").strip()
    if n.lower() in PALETTES:
        return PALETTES[n.lower()].split()
    # one colour ("white", "#fff", "ff8800") or a list ("red,#00e5ff,white") -> solid / custom gradient
    toks = [t for t in re.split(r"[,\s]+", n) if t]
    hexes = [_color_hex(t) for t in toks]
    if toks and all(hexes):
        if len(hexes) == 1:
            hexes = hexes * 2
        return hexes
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
