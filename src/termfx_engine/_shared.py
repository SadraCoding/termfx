#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""termfx-engine - animated terminal header (ASCII art + live effects + sysinfo).

Commands:  height | run FLAG PARENT | preview [SECS] | prepare | art-info [NAME]
           list effects|palettes|art|info-items | distro-logo [NAME] | info | doctor | version
           effect-info [NAME] | palette-show [NAME]
Options:   --set key=value (repeatable)
"""
import errno, glob, hashlib, json, math, os, random, re, select, shutil
import signal, subprocess, sys, time, traceback, unicodedata

VERSION = "2.3.0"
HOME = os.path.expanduser("~")
CONF_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config"), "termfx")
ART_DIR = os.path.join(CONF_DIR, "art")
CONF_FILE = os.path.join(CONF_DIR, "config")
CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "termfx")

DEFAULTS = {
    "enabled": "true", "art": "girl", "effect": "aurora", "palette": "auto",
    "fps": "20", "speed": "1.0", "max_height": "24", "max_width": "0",
    "fit": "auto", "crop": "center", "info": "auto", "info_config": "auto",
    "info_cmd": "", "info_gap": "4", "stars": "true", "glitch": "false",
    "sweep": "true", "intro": "true", "sparkle": "false", "vignette": "false",
    "intensity": "1.0", "frame_ms": "140", "min_cols": "80",
    "min_rows": "24", "reserve": "10", "pause": "auto",
    "truecolor": "auto", "align": "left", "rotate": "false",
    "rotate_interval": "300", "notification": "false", "notify_after": "10",
    "info_colors": "auto", "fetch_preset": "classic",
}
OVERRIDES = {}

# name -> short description (shown by: termfx effect list)
EFFECTS = (
    "aurora", "wave", "rainbow", "plasma", "fire", "matrix", "pulse", "static",
    "spiral", "ripple", "vortex", "scan", "lava", "ocean", "smoke", "neon",
    "cyber", "lightning", "confetti", "comet", "heartbeat", "zebra", "checker",
    "radar", "bloom", "warp", "kaleido", "rain", "snow", "heat", "frost",
    "galaxy", "electric", "hologram", "bounce", "glitchwave", "embers", "tidal",
    "prism", "metaballs", "noise", "stripe", "orbit", "shatter",
    "dna", "fireflies", "crystal", "tunnel", "lissajous", "circuit",
    "sonar", "phosphor", "strobe", "float", "morphean", "pixelrain",
    "ribbons", "embers2", "rainbowroad", "spiralgalaxy", "waterfall",
    "sandstorm", "aurora2", "geometric", "hexgrid", "mandala",
    "clouds", "pulsegrid", "starfield", "magnetic", "firework",
    "ink", "barcode", "topography", "twinkle", "waveform",
    "random",
)
EFFECT_DESC = {
    "aurora": "northern-lights ribbons", "wave": "soft rolling colour wave",
    "rainbow": "classic rainbow sweep", "plasma": "classic plasma blob",
    "fire": "rising flames", "matrix": "falling code rain",
    "pulse": "breathing glow", "static": "still horizontal gradient",
    "spiral": "spinning spiral from centre", "ripple": "expanding water rings",
    "vortex": "swirling black-hole pull", "scan": "CRT horizontal scanline",
    "lava": "molten horizontal flow", "ocean": "deep sea swell",
    "smoke": "drifting soft smoke", "neon": "bright neon edges",
    "cyber": "cyberpunk grid", "lightning": "electric flashes",
    "confetti": "party sparkles", "comet": "diagonal comet trails",
    "heartbeat": "strong double pulse", "zebra": "moving zebra stripes",
    "checker": "animated checkerboard", "radar": "rotating radar sweep",
    "bloom": "soft radial bloom", "warp": "hyperspace warp",
    "kaleido": "kaleidoscope mirrors", "rain": "soft colour rain",
    "snow": "gentle snowfall", "heat": "heat shimmer",
    "frost": "icy crystal shimmer", "galaxy": "deep-space swirl",
    "electric": "jagged voltage", "hologram": "flicker hologram scan",
    "bounce": "bouncing highlight", "glitchwave": "noisy glitch wave",
    "embers": "floating embers", "tidal": "slow tidal wash",
    "prism": "light through a prism", "metaballs": "blobby metaballs",
    "noise": "organic noise field", "stripe": "diagonal racing stripes",
    "orbit": "orbiting colour rings", "shatter": "broken-glass shards",
    "dna": "double-helix undulation", "fireflies": "drifting firefly sparks",
    "crystal": "growing crystal facets", "tunnel": "3D infinite corridor",
    "lissajous": "lissajous curve traces", "circuit": "PCB trace glow",
    "sonar": "pulsing sonar rings", "phosphor": "old CRT phosphor decay",
    "strobe": "rapid strobe flashes", "float": "floating bubbles",
    "morphean": "morphean hexagonal warps", "pixelrain": "pixel-grid rain columns",
    "ribbons": "layered flowing aurora ribbons", "embers2": "dense rising ember field",
    "rainbowroad": "bright winding rainbow bands", "spiralgalaxy": "multi-arm rotating galaxy",
    "waterfall": "cascading water curtains", "sandstorm": "wind-driven desert grains",
    "aurora2": "shimmering polar light curtains", "geometric": "rotating geometric facets",
    "hexgrid": "glowing animated hexagonal grid", "mandala": "radial mandala symmetry",
    "clouds": "slow billowing cloud layers", "pulsegrid": "pulsing perspective grid",
    "starfield": "stars drifting through space", "magnetic": "curved magnetic field lines",
    "firework": "bursts of expanding fireworks", "ink": "ink spreading through water",
    "barcode": "scanning barcode bands", "topography": "animated topographic contours",
    "twinkle": "soft random twinkling lights", "waveform": "layered audio waveform bands",
    "random": "pick a random effect each start",
}
PALETTES = {
    "catppuccin": "f5c2e7 cba6f7 89b4fa 74c7ec 94e2d5 a6e3a1",
    "tokyonight": "ff9ac1 bb9af7 7aa2f7 7dcfff 73daca 9ece6a",
    "rosepine":   "ebbcba c4a7e7 7fb4ca 9ccfd8 95b1ac f6c177",
    "onedark":    "c678dd 61afef 56b6c2 98c379 e5c07b d19a66 e06c75",
    "aurora":     "0b132b 1c7c54 2de1a2 57cc99 80ffdb 7b2cbf c77dff",
    "rainbow":    "ff0040 ff9900 ffee00 33ff66 00ddff 3a5bff b03bff ff0040",
    "ocean":      "0b3d91 1565c0 00acc1 4dd0e1 b2ebf2",
    "sunset":     "3d1a78 c2185b ff5722 ff9800 ffd54f",
    "neon":       "ff00c8 7a00ff 00e5ff 00ff9d",
    "dracula":    "bd93f9 ff79c6 8be9fd 50fa7b f1fa8c",
    "nord":       "5e81ac 81a1c1 88c0d0 8fbcbb a3be8c",
    "gruvbox":    "cc241d d65d0e d79921 98971a 689d6a 458588",
    "forest":     "0b3d0b 1b5e20 388e3c 8bc34a ccff90",
    "fire":       "1a0000 7f0000 d50000 ff6d00 ffd600 fffde7",
    "matrix":     "001a00 005c00 00c800 00ff41 d0ffd8",
    "ice":        "0d1b4c 1e5aa8 5bc0eb 9ee7ff ffffff",
    "mono":       "3a3a3a 8a8a8a cfcfcf ffffff",
    "vaporwave":  "ff71ce b967ff 01cdfe 05ffa1 fffb96",
    "gold":       "5a3a00 b8860b ffd700 fff2a8",
    "cherry":     "2d0a1f 7a1b4d d6336c ff8fb1 ffe0ec",
    "cyberpunk":  "ff0090 00f0ff 7a00ff fcee0a 050505",
    "synthwave":  "2b1055 ff2a6d 05d9e8 d1f7ff ffe66d",
    "midnight":   "0a0e27 1b1f3b 3d348b 7678ed 9b5de5",
    "candy":      "ff6b9d ffc2e2 7afcff b8f2e6 ffe66d",
    "magma":      "1a0000 4a0000 9b2226 e85d04 fca311",
    "arctic":     "e8f1f5 aed9e0 5fa8d3 1b4965 cae9ff",
    "jade":       "004b23 007f5f 2b9348 55a630 80b918",
    "ruby":       "4a0000 9b0000 e63946 ff6b6b ffc9c9",
    "amethyst":   "240046 5a189a 7b2cbf 9d4edd c77dff",
    "pastel":     "ffadad ffd6a5 fdffb6 caffbf 9bf6ff a0c4ff bdb2ff ffc6ff",
    "twilight":   "0d1b2a 1b263b 415a77 778da9 e0e1dd",
    "blood":      "1a0000 6a040f 9d0208 d00000 dc2f02",
    "mint":       "004d40 26a69a 80cbc4 b2dfdb e0f2f1",
    "copper":     "3d1c02 7f4f24 c38e70 ddb892 ffe8d6",
    "ultraviolet":"10002b 240046 5a189a 7b2cbf c77dff e0aaff",
    "retrowave":  "ff2a6d d100d1 05d9e8 01c5c5 fcee0a",
    "emerald":    "002b1a 004d33 008f5a 00c896 7dffc2",
    "sakura":     "2d132c 801336 c72c41 ee6c4d f7b2bd",
    "desert":     "3d2914 8b5e34 c4a484 e6c38a f5e6c8",
    "abyss":      "000814 001d3d 003566 0077b6 00b4d8",
    "toxic":      "0b1a00 39ff14 76ff03 c6ff00 eeff41",
    "royal":      "0b0b2b 1a237e 283593 5c6bc0 9fa8da",
    "peach":      "ffcdb2 ffc8a2 ffb4a2 e5989b b5838d",
    "ink":        "0a0a0a 1a1a2e 16213e 0f3460 e94560",
    "solar":      "fcf6ba f7d060 f4a261 e76f51 9b2226",
    "lunar":      "0d1b2a 1b263b 415a77 778da9 e0e1dd f8f9fa",
    "lava":       "1a0000 7f0000 d50000 ff6d00 ffd600",
    "sky":        "03045e 0077b6 00b4d8 90e0ef caf0f8",
    "berry":      "4a004e 7b2d8e c77dff ff6bcb ffb3de",
    "moss":       "1a2e05 3d550c 6b8f3c a4c26b d4e09b",
    "flamingo":   "ff006e fb5607 ffc300 8338ec 3a86ff",
    "nebula":     "1a0533 4a0e78 9b59b6 e91e63 ff6f61 ffd166",
    "photon":     "000000 001f3f 0074d9 7fdbff b1dcfc ffffff",
    "autumn":     "2d132c 801336 c72c41 e63946 f77461 ffd166 f4a261",
    "neon-noir":  "0a0a0a ff00ff 00ffff ff0066 00ff99 ffff00",
    "copper-mine":"1a0f00 3d2817 7f5539 c59a68 e3b58e f6e7d1",
    "cosmic":     "000004 10002b 3a0ca3 7209b7 f72584",
    "coral":      "003049 d62828 f77f00 fcbf49 eae2b7",
    "lavender":   "2b2d42 52489c 8675a7 b8a0d8 e0cfe8",
    "electric":   "0a0a0a 0d0dff 390099 9d00ff f20089",
    "terra":      "2d2b2a 514940 8e7c65 c7a882 e8d5b7",
    "bloom":      "10002b 5a189a c77dff e0aaff ff9de1 fff5e6",
    "spectrum":   "ff0000 ff8800 ffff00 00ff00 00ffff 0000ff ff00ff ff0000",
    "polar":      "014f86 0196f2 64dfdf aeffcf ff6b6b",
    "vintage":    "2c1810 5c3d21 9a7b4f c4a570 e8d5b0 fff8e7",
    "crimson":    "100002 240014 360019 5c0029 93003e d8004b",
}
EFFECT_PALETTE = {
    "aurora": "aurora", "wave": "catppuccin", "rainbow": "rainbow",
    "plasma": "neon", "fire": "fire", "matrix": "matrix",
    "pulse": "vaporwave", "static": "catppuccin",
    "spiral": "ultraviolet", "ripple": "ocean", "vortex": "midnight",
    "scan": "cyberpunk", "lava": "magma", "ocean": "ocean",
    "smoke": "twilight", "neon": "neon", "cyber": "cyberpunk",
    "lightning": "ice", "confetti": "candy", "comet": "gold",
    "heartbeat": "ruby", "zebra": "mono", "checker": "pastel",
    "radar": "toxic", "bloom": "sakura", "warp": "synthwave",
    "kaleido": "rainbow", "rain": "sky", "snow": "arctic",
    "heat": "solar", "frost": "ice", "galaxy": "midnight",
    "electric": "neon", "hologram": "cyberpunk", "bounce": "candy",
    "glitchwave": "retrowave", "embers": "fire", "tidal": "abyss",
    "prism": "pastel", "metaballs": "amethyst", "noise": "forest",
    "stripe": "flamingo", "orbit": "royal", "shatter": "ink",
    "dna": "nebula", "fireflies": "toxic", "crystal": "ice",
    "tunnel": "ultraviolet", "lissajous": "synthwave", "circuit": "matrix",
    "sonar": "photon", "phosphor": "matrix", "strobe": "neon-noir",
    "float": "candy", "morphean": "amethyst", "pixelrain": "cyberpunk",
    "random": "catppuccin",
    "ribbons": "aurora", "embers2": "fire", "rainbowroad": "rainbow",
    "spiralgalaxy": "cosmic", "waterfall": "ocean", "sandstorm": "desert",
    "aurora2": "polar", "geometric": "spectrum", "hexgrid": "toxic",
    "mandala": "ultraviolet", "clouds": "twilight", "pulsegrid": "cyberpunk",
    "starfield": "photon", "magnetic": "electric", "firework": "flamingo",
    "ink": "ink", "barcode": "mono", "topography": "forest",
    "twinkle": "candy", "waveform": "synthwave",
}
FALLBACK_ART = ["  _                    __       ",
                " | |_ ___ _ __ _ __ ___ / _|_  __  ",
                " | __/ _ \\ '__| '_ ` _ \\ |_\\ \\/ /  ",
                " | ||  __/ |  | | | | | |  _|>  <   ",
                "  \\__\\___|_|  |_| |_| |_|_| /_/\\_\\  "]

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")
CSI_ANY = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
FRAME_RE = re.compile(r"^\s*(?:-{3,}\s*frame\s*-{3,}|%%\s*frame\s*%%)\s*$|^\x0c$", re.I)
UTF8 = "utf" in (os.environ.get("LC_ALL") or os.environ.get("LC_CTYPE") or os.environ.get("LANG") or "utf").lower()
