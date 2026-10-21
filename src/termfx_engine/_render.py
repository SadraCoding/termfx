from ._shared import (
    EFFECTS, EFFECT_PALETTE, UTF8, math, os,
    random, time,
)
from ._system import (
    as_bool, as_float, as_int,
)
from ._color import (
    build_lut, palette_stops, to256, truecolor_on,
)
from ._art import (
    clip_ansi,
)
from ._effects import (
    Fx,
)

class Renderer:
    SCRAMBLE = "01#%&@$▒░" if UTF8 else "01#%&@$"

    def __init__(self, cfg, lay):
        self.cfg, self.lay = cfg, lay
        self.truecolor = truecolor_on(cfg)
        fx = cfg["effect"].strip().lower()
        if fx not in EFFECTS:
            fx = "aurora"
        if fx == "random":
            pool = [e for e in EFFECTS if e != "random"]
            fx = random.Random(os.getpid() ^ int(time.time())).choice(pool)
        pal = cfg["palette"].strip()
        if pal.lower() in ("", "auto"):
            pal = EFFECT_PALETTE.get(fx, "catppuccin")
        self.lut = build_lut(palette_stops(pal))
        self.sp = max(0.1, as_float(cfg["speed"], 1.0))
        self.fx = Fx(fx, lay.aw + 2, lay.H, self.sp)
        self.effect_name = fx
        self.frame_ms = max(40, as_int(cfg["frame_ms"], 140))
        self.stars_on = as_bool(cfg["stars"])
        self.glitch_on = as_bool(cfg["glitch"])
        self.sweep_on = as_bool(cfg["sweep"])
        self.intro_on = as_bool(cfg["intro"])
        self.sparkle_on = as_bool(cfg.get("sparkle", "false"))
        self.vignette_on = as_bool(cfg.get("vignette", "false"))
        self.intensity = max(0.3, min(2.5, as_float(cfg.get("intensity", "1.0"), 1.0)))
        self.cache = {}
        self.stars = {}
        rnd = random.Random(3)
        self.rnd = [[rnd.random() for _ in range(lay.aw + 2)] for _ in range(lay.H)]
        self.star_chars = "·+*✦" if UTF8 else ".+*#"
        self.align = cfg.get("align", "left").strip().lower()
        if self.align == "center":
            self.align_pad = max(0, (lay.cols - lay.aw - 2) // 2)
        elif self.align == "right":
            self.align_pad = max(0, lay.cols - lay.aw - 2)
        else:
            self.align_pad = 0

    def esc(self, x, b):
        b = b * self.intensity
        idx = int(min(max(x, 0.0), 1.0) * 255 + 0.5)
        bq = int(min(max(b, 0.0), 1.6) * 12 + 0.5)
        key = (idx << 5) | bq
        e = self.cache.get(key)
        if e is None:
            r, g, bl = self.lut[idx]
            bb = bq / 12.0
            if bb <= 1.0:
                r, g, bl = int(r * bb), int(g * bb), int(bl * bb)
            else:
                m = min(1.0, (bb - 1.0) / 0.6)
                r, g, bl = int(r + (255 - r) * m), int(g + (255 - g) * m), int(bl + (255 - bl) * m)
            e = ("\x1b[38;2;%d;%d;%dm" % (r, g, bl)) if self.truecolor else ("\x1b[38;5;%dm" % to256(r, g, bl))
            self.cache[key] = e
        return e

    def render(self, t, top=0, save=True):
        L = self.lay
        H, aw, ah = L.H, L.aw, L.ah
        frames = L.frames
        frame = frames[int(t * 1000 / self.frame_ms) % len(frames)] if len(frames) > 1 else frames[0]
        y_off = (H - ah) // 2
        bw = aw + 2
        glitch = {}
        if self.glitch_on and t > 1.5 and random.random() < 0.05:
            for _ in range(random.choice((1, 1, 2, 3))):
                glitch[random.randrange(ah)] = random.choice((-3, -2, -1, 1, 2, 3))
        sw = (t * 28 * self.sp) % (bw + 2 * H + 60) - 25 if self.sweep_on else -9999
        ip = (t / 1.3) if (self.intro_on and t < 1.3) else None
        stars = self.stars
        spawn = 6 if self.sparkle_on else (3 if self.stars_on else 0)
        if spawn:
            for _ in range(spawn):
                r, c = random.randrange(H), random.randrange(bw)
                ar = r - y_off
                if not (0 <= ar < ah and c < len(frame[ar] if ar < len(frame) else []) and frame[ar][c] not in (" ", "")):
                    stars[(r, c)] = random.randint(6, 18 if self.sparkle_on else 15)
        esc, fx = self.esc, self.fx
        g_mag, g_cyan = "\x1b[38;2;255;80;220m", "\x1b[38;2;80;255;255m"
        cx, cy = (bw - 1) / 2.0, (H - 1) / 2.0
        vmax = math.hypot(cx, cy) or 1.0
        buf = ["\x1b[?2026h"]
        if save:
            buf.append("\x1b7")
        buf.append("\x1b[?7l")
        for r in range(H):
            ar = r - y_off
            row = frame[ar] if 0 <= ar < len(frame) else None
            shift = glitch.get(ar, 0)
            parts = ["\x1b[%d;%dH" % (top + r + 1, self.align_pad + 1)]
            last = None
            rn = self.rnd[r]
            for c in range(bw):
                sc = c - shift
                ch = row[sc] if (row is not None and 0 <= sc < len(row)) else " "
                if ch == "":
                    continue
                if ch != " ":
                    if ip is not None and rn[c] * 0.7 + c / bw * 0.3 > ip * 1.02:
                        ch = random.choice(self.SCRAMBLE) if random.random() < 0.5 else " "
                        col = esc(0.1, 0.55)
                    elif shift:
                        col = g_mag if (c + ar) & 1 else g_cyan
                    else:
                        x, b = fx(r, c, t)
                        d = abs((c + 2 * r) - sw)
                        if d < 3:
                            b = max(b, 1.0) + (3 - d) * 0.2
                        if self.vignette_on:
                            b *= max(0.35, 1.0 - math.hypot(c - cx, r - cy) / vmax * 0.55)
                        col = esc(x, b)
                else:
                    life = stars.get((r, c)) if stars else None
                    if life:
                        ch = self.star_chars[min(3, life // 4)]
                        col = esc(0.9, 1.6) if life > 9 else (esc(0.55, 1.0) if life > 4 else esc(0.3, 0.55))
                    else:
                        parts.append(" ")
                        continue
                if col != last:
                    parts.append(col)
                    last = col
                parts.append(ch)
            parts.append("\x1b[0m")
            buf.append("".join(parts))
        info = L.info
        if info:
            iy = max(0, (H - len(info)) // 2)
            room = L.cols - L.info_col
            for i, l in enumerate(info[:H]):
                buf.append("\x1b[%d;%dH%s\x1b[0m\x1b[K" % (top + iy + i + 1, L.info_col + 1, clip_ansi(l, room)))
        buf.append("\x1b[0m\x1b[?7h")
        if save:
            buf.append("\x1b8")
        buf.append("\x1b[?2026l")
        self.stars = {k: v - 1 for k, v in stars.items() if v > 1}
        return "".join(buf)
