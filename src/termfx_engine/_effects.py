from ._shared import (
    math, random,
)

def tri(x):
    x %= 1.0
    return 1 - abs(2 * x - 1)

def _hash2(x, y):
    return math.sin(x * 127.1 + y * 311.7) * 43758.5453 % 1.0

class Fx:
    def __init__(self, name, W, H, speed):
        self.W, self.H, self.sp = max(W, 1), max(H, 1), speed
        self.name = name
        self.fn = getattr(self, "fx_" + name, self.fx_aurora)
        rnd = random.Random(7)
        n = self.W + 4
        if name in ("matrix", "rain", "snow", "embers", "lightning"):
            self.spd = [rnd.uniform(4, 16) for _ in range(n)]
            self.off = [rnd.uniform(0, self.H + 16) for _ in range(n)]
            self.trl = [rnd.randint(max(3, self.H // 4), max(5, self.H)) for _ in range(n)]
            self.hue = [rnd.random() for _ in range(n)]
        if name in ("comet", "shatter"):
            self.comets = [(rnd.uniform(0, 1), rnd.uniform(0.4, 1.4), rnd.uniform(0, 1)) for _ in range(8)]
        if name == "metaballs":
            self.balls = [(rnd.uniform(0.2, 0.8), rnd.uniform(0.2, 0.8), rnd.uniform(0.08, 0.18),
                           rnd.uniform(0.4, 1.2), rnd.uniform(0.4, 1.2)) for _ in range(5)]

    def __call__(self, r, c, t):
        return self.fn(r, c, t * self.sp)

    def fx_wave(self, r, c, t):
        return tri(c * 0.011 + r * 0.028 - t * 0.22), 1.0

    def fx_rainbow(self, r, c, t):
        return (c * 0.010 + r * 0.02 - t * 0.18) % 1.0, 1.0

    def fx_aurora(self, r, c, t):
        v = 0.5 + 0.28 * math.sin(c * 0.075 + t * 0.9) + 0.22 * math.sin(r * 0.42 - t * 0.7 + c * 0.02)
        return v, 0.78 + 0.22 * math.sin(c * 0.045 - t * 1.4 + r * 0.25)

    def fx_plasma(self, r, c, t):
        v = (math.sin(c * 0.11 + t) + math.sin(r * 0.45 - t * 1.3) + math.sin(c * 0.06 + r * 0.3 + t * 0.7)
             + math.sin(math.hypot(c - self.W / 2, (r - self.H / 2) * 2.1) * 0.14 - t))
        return (v + 4) / 8, 1.0

    def fx_fire(self, r, c, t):
        h = r / max(self.H - 1, 1)
        x = 0.14 + 0.82 * h ** 1.1 + 0.12 * math.sin(c * 0.31 + t * 5) * (1 - h) + random.random() * 0.07
        return x, 0.85 + random.random() * 0.15

    def fx_matrix(self, r, c, t):
        i = c % len(self.spd)
        trail = self.trl[i]
        d = (t * self.spd[i] + self.off[i]) % (self.H + trail + 6) - r
        if 0 <= d < trail:
            k = 1 - d / trail
            return (0.98, 1.3) if d < 1 else (0.45 + 0.45 * k, 0.55 + 0.45 * k)
        return 0.35, 0.42

    def fx_pulse(self, r, c, t):
        p = 0.5 + 0.5 * math.sin(t * 1.6)
        return 0.2 + 0.6 * p * (0.6 + 0.4 * r / max(self.H - 1, 1)), 0.7 + 0.3 * p

    def fx_static(self, r, c, t):
        return c / max(self.W - 1, 1) * 0.9, 1.0

    def fx_spiral(self, r, c, t):
        dx, dy = c - self.W / 2, (r - self.H / 2) * 2.0
        ang = math.atan2(dy, dx) / (2 * math.pi) + 0.5
        dist = math.hypot(dx, dy) / max(self.W, 1)
        return (ang + dist * 2 - t * 0.35) % 1.0, 0.7 + 0.3 * (1 - min(dist, 1))

    def fx_ripple(self, r, c, t):
        dx, dy = (c - self.W / 2) / max(self.W, 1), (r - self.H / 2) / max(self.H, 1)
        d = math.hypot(dx * 1.6, dy)
        return (d * 4 - t * 0.9) % 1.0, 0.55 + 0.45 * abs(math.sin(d * 18 - t * 4))

    def fx_vortex(self, r, c, t):
        dx, dy = c - self.W / 2, (r - self.H / 2) * 2.2
        ang = math.atan2(dy, dx)
        dist = math.hypot(dx, dy) / max(self.W * 0.5, 1)
        return (ang / (2 * math.pi) + 0.5 + t * 0.2 - dist) % 1.0, max(0.35, 1.2 - dist)

    def fx_scan(self, r, c, t):
        line = (t * 8) % (self.H + 2)
        prox = 1 - min(abs(r - line) / 3.0, 1)
        base = (c / max(self.W - 1, 1) + t * 0.05) % 1.0
        return base, 0.45 + prox * 0.9

    def fx_lava(self, r, c, t):
        h = r / max(self.H - 1, 1)
        x = (c * 0.04 + t * 0.5 + math.sin(r * 0.4 + t) * 0.2) % 1.0
        return 0.15 + x * 0.7 + h * 0.15, 0.7 + 0.3 * h + random.random() * 0.1

    def fx_ocean(self, r, c, t):
        v = 0.5 + 0.25 * math.sin(c * 0.08 + t * 1.1) + 0.2 * math.sin(r * 0.55 - t * 0.8)
        depth = r / max(self.H - 1, 1)
        return v % 1.0, 0.55 + 0.45 * (1 - depth * 0.6)

    def fx_smoke(self, r, c, t):
        v = (math.sin(c * 0.07 + t * 0.4) + math.sin(r * 0.2 - t * 0.3) + math.sin((c + r) * 0.05 + t * 0.2)) / 6 + 0.5
        return v, 0.45 + 0.25 * math.sin(c * 0.03 - t)

    def fx_neon(self, r, c, t):
        edge = min(c, self.W - 1 - c, r * 2, (self.H - 1 - r) * 2) / max(self.W * 0.15, 1)
        pulse = 0.5 + 0.5 * math.sin(t * 3 + c * 0.1)
        return (c / max(self.W, 1) + t * 0.1) % 1.0, 0.5 + 0.7 * max(0, 1 - edge) * pulse

    def fx_cyber(self, r, c, t):
        grid = 1.0 if (c % 6 == 0 or r % 3 == 0) else 0.35
        return (c * 0.02 + r * 0.05 + t * 0.15) % 1.0, 0.4 + 0.6 * grid

    def fx_lightning(self, r, c, t):
        i = c % len(self.spd)
        bolt = abs(math.sin(t * self.spd[i] * 0.3 + self.off[i]))
        flash = bolt > 0.92
        jag = abs(r - (self.H / 2 + math.sin(c * 0.4 + t * 8) * self.H * 0.3))
        if flash and jag < 2:
            return self.hue[i], 1.5
        return 0.55, 0.35 + (0.4 if jag < 4 else 0)

    def fx_confetti(self, r, c, t):
        h = _hash2(c + int(t * 3), r)
        spark = _hash2(c * 3, r + int(t * 5))
        return h, 0.5 + 0.9 * (1 if spark > 0.88 else 0.15)

    def fx_comet(self, r, c, t):
        best = 0.0
        hue = 0.5
        ny, nx = r / max(self.H, 1), c / max(self.W, 1)
        for oh, sp, ph in self.comets:
            pos = (t * sp + ph) % 1.4 - 0.2
            d = abs(ny - (oh + (nx - 0.5) * 0.3) - (pos - nx) * 0.15) + abs(nx - pos) * 0.5
            if d < 0.12:
                k = 1 - d / 0.12
                if k > best:
                    best, hue = k, (oh + ph) % 1.0
        return hue, 0.4 + best * 1.1

    def fx_heartbeat(self, r, c, t):
        # double-beat: two peaks per cycle
        phase = (t * 1.4) % 1.0
        beat = math.exp(-((phase - 0.15) * 12) ** 2) + 0.6 * math.exp(-((phase - 0.35) * 12) ** 2)
        dist = math.hypot(c - self.W / 2, (r - self.H / 2) * 2) / max(self.W * 0.5, 1)
        return 0.1 + 0.6 * beat + 0.2 * (1 - dist), 0.5 + beat * 0.9

    def fx_zebra(self, r, c, t):
        v = ((c + r * 0.5 + t * 8) / 5) % 2
        return 0.15 if v < 1 else 0.85, 1.0

    def fx_checker(self, r, c, t):
        cell = int(c / 4 + t * 2) + int(r / 2 + t)
        return (0.2 if cell % 2 == 0 else 0.8), 0.95

    def fx_radar(self, r, c, t):
        dx, dy = c - self.W / 2, (r - self.H / 2) * 2
        ang = (math.atan2(dy, dx) / (2 * math.pi) + 0.5 + t * 0.25) % 1.0
        dist = math.hypot(dx, dy) / max(self.W * 0.55, 1)
        beam = 1 - min(ang * 8, 1) if ang < 0.12 else 0.2
        rings = abs(math.sin(dist * 12))
        return (dist + t * 0.1) % 1.0, 0.35 + beam * 0.9 + rings * 0.2

    def fx_bloom(self, r, c, t):
        dx, dy = (c - self.W / 2) / max(self.W, 1), (r - self.H / 2) / max(self.H, 1)
        d = math.hypot(dx * 1.4, dy)
        pulse = 0.5 + 0.5 * math.sin(t * 1.5)
        return (0.3 + d * 0.5 + t * 0.05) % 1.0, max(0.3, (1.1 - d) * (0.7 + 0.3 * pulse))

    def fx_warp(self, r, c, t):
        dx, dy = c - self.W / 2, r - self.H / 2
        dist = math.hypot(dx, dy * 2) / max(self.W * 0.5, 1) + 0.01
        ang = math.atan2(dy, dx) / (2 * math.pi) + 0.5
        return (ang + 1 / dist * 0.3 - t * 0.5) % 1.0, min(1.4, 0.4 + 0.8 / dist)

    def fx_kaleido(self, r, c, t):
        dx, dy = abs(c - self.W / 2), abs(r - self.H / 2)
        mx, my = min(dx, self.W / 2 - dx), min(dy, self.H / 2 - dy)
        return (mx * 0.04 + my * 0.08 + t * 0.2) % 1.0, 0.75 + 0.25 * math.sin(mx * 0.3 + t)

    def fx_rain(self, r, c, t):
        i = c % len(self.spd)
        d = (t * self.spd[i] * 0.7 + self.off[i]) % (self.H + 4) - r
        if 0 <= d < 3:
            return self.hue[i], 1.0 - d / 3
        return 0.4, 0.3

    def fx_snow(self, r, c, t):
        i = c % len(self.spd)
        wobble = math.sin(t * 1.5 + self.off[i]) * 2
        d = (t * self.spd[i] * 0.35 + self.off[i]) % (self.H + 6) - r
        cc = (c + int(wobble)) % max(self.W, 1)
        if abs(cc - c) < 2 and 0 <= d < 2:
            return 0.85, 1.2 - d * 0.3
        return 0.55, 0.35

    def fx_heat(self, r, c, t):
        h = 1 - r / max(self.H - 1, 1)
        shim = math.sin(c * 0.5 + t * 6 + r) * 0.08
        return 0.2 + h * 0.7 + shim, 0.6 + h * 0.5

    def fx_frost(self, r, c, t):
        crystal = abs(math.sin(c * 0.35 + t * 0.5) * math.cos(r * 0.55 - t * 0.3))
        return 0.55 + crystal * 0.35, 0.5 + crystal * 0.7

    def fx_galaxy(self, r, c, t):
        dx, dy = c - self.W / 2, (r - self.H / 2) * 2
        ang = math.atan2(dy, dx) / (2 * math.pi) + 0.5
        dist = math.hypot(dx, dy) / max(self.W * 0.5, 1)
        arm = math.sin(ang * 4 * math.pi + dist * 6 - t)
        return (ang + dist * 0.5 + t * 0.05) % 1.0, 0.4 + 0.5 * max(0, arm) * (1 - dist * 0.5)

    def fx_electric(self, r, c, t):
        jag = abs(math.sin(c * 0.9 + t * 7) * 3 + math.sin(c * 0.3 - t * 3) * 2)
        near = abs(r - self.H / 2 - jag) 
        return (c * 0.03 + t * 0.2) % 1.0, 0.35 + max(0, 1 - near / 2.5) * 1.1

    def fx_hologram(self, r, c, t):
        scan = abs(math.sin(r * 1.2 - t * 5))
        flicker = 0.85 + 0.15 * (1 if _hash2(int(t * 20), r) > 0.3 else 0)
        return (c * 0.015 + t * 0.08) % 1.0, (0.45 + scan * 0.5) * flicker

    def fx_bounce(self, r, c, t):
        y = abs((t * 2) % 2 - 1) * (self.H - 1)
        x = (t * 9) % (self.W + 10) - 5
        d = math.hypot(c - x, (r - y) * 2)
        return (t * 0.15) % 1.0, max(0.35, 1.3 - d / 4)

    def fx_glitchwave(self, r, c, t):
        base = tri(c * 0.02 + r * 0.04 - t * 0.3)
        noise = (_hash2(c + int(t * 10), r) - 0.5) * 0.4
        tear = 0.5 if _hash2(r, int(t * 4)) > 0.92 else 0
        return (base + noise + tear) % 1.0, 0.7 + tear * 0.5

    def fx_embers(self, r, c, t):
        i = c % len(self.spd)
        d = self.H - ((t * self.spd[i] * 0.4 + self.off[i]) % (self.H + 8)) - r
        if abs(d) < 1.5:
            return 0.2 + self.hue[i] * 0.4, 1.2
        h = r / max(self.H - 1, 1)
        return 0.1 + h * 0.3, 0.4

    def fx_tidal(self, r, c, t):
        tide = 0.5 + 0.5 * math.sin(t * 0.7)
        shore = r / max(self.H - 1, 1)
        foam = abs(shore - tide)
        return (c * 0.01 + t * 0.05) % 1.0, 0.4 + max(0, 1 - foam * 4) * 0.7

    def fx_prism(self, r, c, t):
        band = (c / max(self.W, 1) + r * 0.02 + t * 0.1) % 1.0
        shine = abs(math.sin(c * 0.2 - t * 2))
        return band, 0.6 + shine * 0.5

    def fx_metaballs(self, r, c, t):
        nx, ny = c / max(self.W, 1), r / max(self.H, 1)
        field = 0.0
        for bx, by, rad, sx, sy in self.balls:
            px = 0.5 + 0.35 * math.sin(t * sx + bx * 6)
            py = 0.5 + 0.35 * math.cos(t * sy + by * 6)
            d2 = (nx - px) ** 2 + (ny - py) ** 2 + 1e-6
            field += (rad * rad) / d2
        v = min(field / 3.0, 1.0)
        return v, 0.4 + v * 0.9

    def fx_noise(self, r, c, t):
        n = (_hash2(c * 0.3 + t, r * 0.3) + _hash2(c * 0.1 - t * 0.5, r * 0.2) +
             _hash2(c * 0.05, r * 0.05 + t * 0.2)) / 3
        return n, 0.55 + n * 0.45

    def fx_stripe(self, r, c, t):
        return ((c + r + t * 12) / 7) % 1.0, 1.0

    def fx_orbit(self, r, c, t):
        dx, dy = c - self.W / 2, (r - self.H / 2) * 2
        dist = math.hypot(dx, dy)
        ring = abs(math.sin(dist * 0.25 - t * 2))
        ang = (math.atan2(dy, dx) / (2 * math.pi) + 0.5 + t * 0.15) % 1.0
        return ang, 0.4 + ring * 0.8

    def fx_shatter(self, r, c, t):
        piece = int(_hash2(c // 5, r // 2) * 12)
        offset = math.sin(t * 1.5 + piece) * 0.2
        return (piece / 12 + offset + t * 0.05) % 1.0, 0.6 + 0.4 * abs(math.sin(t + piece))

    def fx_random(self, r, c, t):
        return self.fx_aurora(r, c, t)

    def fx_dna(self, r, c, t):
        phase = r / max(self.H - 1, 1) * math.pi * 2 + t * 1.8
        x1 = math.sin(phase) * self.W * 0.35 + self.W / 2
        x2 = math.sin(phase + math.pi) * self.W * 0.35 + self.W / 2
        d1 = abs(c - x1)
        d2 = abs(c - x2)
        if d1 < 2 or d2 < 2:
            bridge = 1.0 if (d1 < 2 and d2 < 2 and abs(x1 - x2) > 4) else 0.0
            return (phase / (2 * math.pi) + t * 0.1) % 1.0, 0.9 + bridge * 0.4
        return 0.5, 0.3

    def fx_fireflies(self, r, c, t):
        best, hue = 0.0, 0.5
        for i in range(8):
            fx_ = (math.sin(t * 0.4 + i * 2.3) * 0.3 + 0.5) * self.W
            fy_ = (math.cos(t * 0.3 + i * 1.7) * 0.3 + 0.5) * self.H
            d = math.hypot(c - fx_, (r - fy_) * 2)
            glow = max(0, 1 - d / 5) * (0.5 + 0.5 * math.sin(t * 3 + i * 4))
            if glow > best:
                best, hue = glow, (0.15 + i * 0.1) % 1.0
        return hue, 0.3 + best * 1.2

    def fx_crystal(self, r, c, t):
        nx, ny = (c - self.W / 2) / max(self.W, 1), (r - self.H / 2) / max(self.H, 1)
        ang = math.atan2(ny, nx) / (2 * math.pi) + 0.5
        facets = int(ang * 6 + t * 0.2) % 6
        growth = abs(math.sin(t * 0.8 + facets * 1.05)) * 0.6 + 0.4
        d = math.hypot(nx * 1.6, ny)
        return (facets / 6 + t * 0.05) % 1.0, growth * max(0.3, 1 - d * 0.7)

    def fx_tunnel(self, r, c, t):
        dx, dy = (c - self.W / 2) / max(self.W * 0.5, 1), (r - self.H / 2) / max(self.H * 0.5, 1)
        d = math.hypot(dx, dy) + 0.01
        ang = math.atan2(dy, dx)
        depth = 1.0 / d
        u = (ang / (2 * math.pi) + 0.5) * 4
        stripe = int(u + depth * 3 - t * 2) % 2
        return (depth * 0.3 + t * 0.1) % 1.0, (0.8 if stripe else 0.4) * min(1.2, depth * 0.6)

    def fx_lissajous(self, r, c, t):
        best = 0.0
        for a, b, delta in ((3, 2, 0.5), (5, 4, 1.2), (2, 3, 0.8)):
            px = (math.sin(a * (t * 0.8 + c * 0.12) + delta) * 0.4 + 0.5) * self.W
            py = (math.sin(b * (t * 0.8 + c * 0.12)) * 0.4 + 0.5) * self.H
            d = math.hypot(c - px, r - py)
            best = max(best, max(0, 1 - d / 4))
        return (t * 0.1 + c * 0.02) % 1.0, 0.35 + best * 1.1

    def fx_circuit(self, r, c, t):
        gx, gy = c // 4, r // 2
        trace = 1.0 if (c % 4 == 0 or r % 2 == 0) else 0.0
        node = 1.0 if (c % 4 == 0 and r % 2 == 0) else 0.0
        pulse = max(0, 1 - abs((c + r * 3 - int(t * 12) * 8) % 30) / 4)
        sig = _hash2(gx, gy)
        gate = 1 if sig > 0.7 else 0
        return (sig + t * 0.05) % 1.0, (0.3 + trace * 0.4 + node * 0.6 + pulse * 0.9 + gate * 0.3)

    def fx_sonar(self, r, c, t):
        dx, dy = c - self.W / 2, (r - self.H / 2) * 2
        d = math.hypot(dx, dy)
        ring = (d - t * 12) % 18
        intensity = max(0, 1 - ring / 3) if ring < 3 else 0
        return (d * 0.02 + t * 0.08) % 1.0, 0.25 + intensity * 1.1

    def fx_phosphor(self, r, c, t):
        decay = max(0, 1 - ((t * 4 + c * 0.5 + r * 1.2) % 20) / 12)
        flicker = 0.9 + 0.1 * math.sin(t * 15 + c * 2)
        scan = 1.0 if (r + int(t * 2)) % 3 != 0 else 0.6
        return 0.35, decay * flicker * scan * 0.85

    def fx_strobe(self, r, c, t):
        phase = int(t * 6) % 4
        if phase == 0:
            return (c * 0.03 + r * 0.05) % 1.0, 1.5
        elif phase == 2:
            return (c * 0.03 + r * 0.05 + 0.5) % 1.0, 1.4
        return (c * 0.03 + r * 0.05) % 1.0, 0.2

    def fx_float(self, r, c, t):
        best, hue = 0.0, 0.5
        for i in range(6):
            bx = (math.sin(t * 0.3 + i * 1.8) * 0.35 + 0.5) * self.W
            by = self.H - ((t * (2 + i * 0.5) + i * 7) % (self.H + 10))
            rad = 3 + i * 1.5
            d = math.hypot(c - bx, (r - by) * 1.5)
            shell = max(0, 1 - abs(d - rad) / 2)
            if shell > best:
                best, hue = shell, (0.55 + i * 0.07) % 1.0
        return hue, 0.3 + best * 1.0

    def fx_morphean(self, r, c, t):
        nx = (c - self.W / 2) / max(self.W, 1)
        ny = (r - self.H / 2) / max(self.H, 1)
        warp = math.sin(nx * 6 + t) * math.cos(ny * 4 - t * 0.7)
        hex_ = abs(math.sin((nx + warp * 0.2) * 8)) * abs(math.cos((ny - warp * 0.15) * 6))
        return (hex_ * 0.5 + t * 0.06) % 1.0, 0.4 + hex_ * 0.8

    def fx_pixelrain(self, r, c, t):
        col_seed = _hash2(c, 0)
        speed = 3 + col_seed * 8
        drop = (t * speed + col_seed * 20) % (self.H + 8)
        dist = r - drop
        if 0 <= dist < 6:
            k = 1 - dist / 6
            return (col_seed + t * 0.05) % 1.0, 0.6 + k * 0.8
        return col_seed, 0.25
