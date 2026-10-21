from ._shared import (
    CACHE_DIR, CONF_DIR, EFFECT_PALETTE, json, os,
    shutil, subprocess, time,
)
from ._color import (
    build_lut, palette_stops,
)
from ._art import (
    keep_sgr,
)

def _run(argv, timeout=5, shell=False):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, shell=shell,
                           stdin=subprocess.DEVNULL, errors="replace")
        return p.stdout
    except Exception:
        return ""

def _info_palette_colors(cfg):
    """Return a list of 'R;G;B' strings for info panel labels based on info_colors config."""
    mode = (cfg.get("info_colors") or "auto").strip().lower()
    if mode == "off":
        return ["200;200;200"] * 8
    if mode == "rainbow":
        return ["245;194;231", "203;166;247", "137;180;250", "116;199;236",
                "148;226;213", "166;227;161", "249;226;175", "250;179;135"]
    # resolve palette: named palette, or auto = use header palette
    pal_name = mode
    if pal_name in ("", "auto"):
        pal_name = (cfg.get("palette") or "auto").strip().lower()
        if pal_name in ("", "auto"):
            fx = (cfg.get("effect") or "aurora").strip().lower()
            pal_name = EFFECT_PALETTE.get(fx, "catppuccin")
    stops = palette_stops(pal_name)
    lut = build_lut(stops, max(len(stops), 8))
    return ["%d;%d;%d" % (r, g, b) for r, g, b in lut[:8]]

def builtin_info(cfg=None):
    def rd(p):
        try:
            with open(p, errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""
    osn = "Linux"
    for l in rd("/etc/os-release").splitlines():
        if l.startswith("PRETTY_NAME="):
            osn = l.split("=", 1)[1].strip().strip('"')
    un = os.uname()
    up = ""
    try:
        sec = int(float(rd("/proc/uptime").split()[0]))
        d, r = divmod(sec, 86400)
        h, r = divmod(r, 3600)
        up = " ".join(x for x in ((str(d) + "d") if d else "", (str(h) + "h") if h else "", str(r // 60) + "m") if x)
    except Exception:
        pass
    cpu = ""
    for l in rd("/proc/cpuinfo").splitlines():
        if l.lower().startswith("model name"):
            cpu = l.split(":", 1)[1].strip()
            break
    mem = ""
    try:
        mi = {}
        for l in rd("/proc/meminfo").splitlines():
            k, _, v = l.partition(":")
            if v.split():
                mi[k] = int(v.split()[0])
        tot = mi["MemTotal"] / 1048576
        mem = "%.1f / %.1f GiB" % (tot - mi["MemAvailable"] / 1048576, tot)
    except Exception:
        pass
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or "user"
    shell = os.path.basename(os.environ.get("SHELL", "?"))
    term = os.environ.get("TERM_PROGRAM") or os.environ.get("TERM", "")
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    wm = os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DESKTOP_SESSION", "")
    # gather all available info items
    all_items = [
        ("OS", osn), ("Kernel", un.release), ("Uptime", up),
        ("Shell", shell), ("Term", term), ("Desktop", desktop),
        ("WM", wm), ("CPU", cpu), ("Memory", mem),
    ]
    # preset decides which items to show
    preset = (cfg or {}).get("fetch_preset", "classic")
    PRESET_KEYS = {
        "classic":   {"OS", "Kernel", "Uptime", "Shell", "Term", "Desktop", "CPU", "Memory"},
        "compact":   {"OS", "Kernel", "Uptime", "Shell", "CPU", "Memory"},
        "minimal":   {"OS", "Kernel", "Uptime"},
        "clean":     {"OS", "Kernel", "Uptime", "Shell", "Term", "CPU", "Memory", "Desktop"},
        "full":      {"OS", "Kernel", "Uptime", "Shell", "Term", "Desktop", "WM", "CPU", "Memory"},
        "gamer":     {"OS", "Kernel", "CPU", "Memory"},
        "server":    {"OS", "Kernel", "Uptime", "Memory"},
        "developer": {"OS", "Kernel", "Shell", "Term", "WM", "CPU", "Memory"},
        "aesthetic": {"OS", "Kernel", "Uptime", "Shell", "Term", "Memory"},
        "hybridfetch": {"OS", "Kernel", "Uptime", "Shell", "Term", "CPU", "Memory", "Desktop"},
        "ultra":     {"OS", "Kernel", "Uptime", "Shell", "Term", "Desktop", "WM", "CPU", "Memory"},
    }
    wanted = PRESET_KEYS.get(preset, PRESET_KEYS["classic"])
    items = [(k, v) for k, v in all_items if k in wanted]
    cols = _info_palette_colors(cfg) if cfg else [
        "245;194;231", "203;166;247", "137;180;250", "116;199;236",
        "148;226;213", "166;227;161", "249;226;175", "250;179;135"]
    lines = ["\x1b[1;38;2;%sm%s\x1b[0m\x1b[38;2;%sm@\x1b[1;38;2;%sm%s\x1b[0m" % (
        cols[0], user, cols[2 % len(cols)], cols[1 % len(cols)], un.nodename),
             "\x1b[38;2;108;112;134m" + "─" * (len(user) + len(un.nodename) + 1) + "\x1b[0m"]
    for i, (k, v) in enumerate(items):
        if v:
            lines.append("\x1b[1;38;2;%sm%-8s\x1b[0m\x1b[38;2;%sm%s\x1b[0m" % (cols[i % len(cols)], k, cols[(i + 1) % len(cols)], v))
    lines.append("")
    lines.append("".join("\x1b[38;2;%sm●\x1b[0m " % c for c in cols))
    return lines

def get_info(cfg):
    mode = cfg["info"].strip().lower()
    if mode in ("off", "none", "false", "0", "no"):
        return []
    sig = "%s|%s|%s|%s" % (mode, cfg["info_cmd"], cfg["info_config"], os.environ.get("TERMFX_SEED", ""))
    cp = os.path.join(CACHE_DIR, "info.json")
    try:
        with open(cp, encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("sig") == sig and time.time() - d.get("ts", 0) < 20:
            return d["lines"]
    except Exception:
        pass
    lines = ""
    cmd = cfg["info_cmd"].strip()
    if cmd:
        lines = _run(cmd, shell=True)
    elif mode in ("auto", "fastfetch") and shutil.which("fastfetch"):
        argv = ["fastfetch", "--logo", "none", "--pipe", "false"]
        ic = cfg["info_config"]
        if ic == "auto":
            ic = os.path.join(CONF_DIR, "fastfetch.jsonc")
        if ic and os.path.isfile(os.path.expanduser(ic)):
            argv += ["--config", os.path.expanduser(ic)]
        lines = _run(argv)
    elif mode in ("auto", "neofetch") and shutil.which("neofetch"):
        lines = _run(["neofetch", "--off"])
    res = [keep_sgr(l).rstrip() for l in lines.split("\n")] if lines else []
    while res and not res[-1].strip():
        res.pop()
    if not res:
        res = builtin_info(cfg)
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump({"sig": sig, "ts": time.time(), "lines": res}, fh, ensure_ascii=False)
    except Exception:
        pass
    return res
