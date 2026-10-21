"""termfx-engine - animated terminal header (ASCII art + live effects + sysinfo).

Commands:  height | run FLAG PARENT | preview [SECS] | prepare | art-info [NAME]
           list effects|palettes|art|info-items | distro-logo [NAME] | info | doctor | version
           effect-info [NAME] | palette-show [NAME]
Options:   --set key=value (repeatable)
"""

from ._shared import (
    ANSI_RE, ART_DIR, CACHE_DIR, CONF_FILE, EFFECTS,
    EFFECT_DESC, EFFECT_PALETTE, OVERRIDES, PALETTES,
    UTF8, VERSION, errno, glob, os,
    random, re, select, shutil, signal,
    sys, time,
)
from ._system import (
    Out, alive, as_bool, as_float, as_int,
    load_config, log_error, term_size,
)
from ._color import (
    build_lut, hex_rgb, truecolor_on,
)
from ._art import (
    parse_art, resolve_art,
)
from ._info import (
    _info_palette_colors, _run, get_info,
)
from ._layout import (
    build_layout,
)
from ._render import (
    Renderer,
)

def write_state(flag, H, parent):
    try:
        tmp = flag + ".state.%d" % os.getpid()
        with open(tmp, "w") as fh:
            fh.write("%d %d %d\n" % (os.getpid(), H, parent))
        os.replace(tmp, flag + ".state")
    except OSError:
        pass

def hide_header(out, height):
    """Release the reserved header area and erase only its rows."""
    out.write("\x1b7\x1b[r\x1b[1;1H")
    for row in range(max(0, height)):
        out.write("\x1b[2K")
        if row + 1 < height:
            out.write("\x1b[1B")
    out.write("\x1b8\x1b[r")

def cmd_run(flag, parent):
    out = Out()
    stop = {"v": False, "reload": False}
    signal.signal(signal.SIGTERM, lambda *a: stop.__setitem__("v", True))
    signal.signal(signal.SIGHUP, lambda *a: stop.__setitem__("v", True))
    signal.signal(signal.SIGUSR1, lambda *a: stop.__setitem__("reload", True))
    for s in ("SIGINT", "SIGTTOU", "SIGTTIN", "SIGPIPE"):
        try:
            signal.signal(getattr(signal, s), signal.SIG_IGN)
        except Exception:
            pass
    cfg = load_config()
    last_size = None
    rend = None
    region_H = 0
    paused = False
    first = True
    t0 = time.time()
    last_rotate = t0
    try:
        while not stop["v"] and alive(parent):
            try:
                rebuild = False
                resuming = False
                if os.path.exists(flag):
                    if not paused:
                        if region_H:
                            hide_header(out, region_H)
                            region_H = 0
                        paused = True
                        write_state(flag, 0, parent)
                elif paused:
                    paused = False
                    resuming = True
                    rebuild = True
                if paused:
                    # A command is printing: never touch the screen, the scroll region or the
                    # layout now (a pending reload/resize is applied when the header returns).
                    time.sleep(0.1)
                    continue
                if stop["reload"]:
                    stop["reload"] = False
                    cfg = load_config()
                    try:
                        os.remove(os.path.join(CACHE_DIR, "info.json"))
                    except OSError:
                        pass
                    rebuild = True
                    t0 = time.time()
                    last_rotate = t0
                # auto-rotate effects/palettes
                if as_bool(cfg.get("rotate", "false")):
                    interval = max(30, as_int(cfg.get("rotate_interval", "300"), 300))
                    if time.time() - last_rotate >= interval:
                        pool = [e for e in EFFECTS if e != "random"]
                        cfg["effect"] = random.choice(pool)
                        cfg["palette"] = "auto"
                        last_rotate = time.time()
                        rebuild = True
                size = term_size()
                if size != last_size or rebuild:
                    last_size = size
                    new = build_layout(cfg, size[0], size[1])
                    if new is None:
                        if region_H:
                            out.write("\x1b[r")
                            region_H = 0
                        rend = None
                        write_state(flag, 0, parent)
                    else:
                        rend = Renderer(cfg, new)
                        if first:
                            out.write("\x1b7\x1b[%d;%dr\x1b8" % (new.H + 1, size[1]))
                            region_H = new.H
                        elif new.H != region_H and resuming:
                            out.write("\x1b7\x1b[%d;%dr\x1b8" % (new.H + 1, size[1]))
                            region_H = new.H
                        elif new.H != region_H:
                            out.write("\x1b[2J\x1b[%d;%dr\x1b[%d;1H" % (new.H + 1, size[1], new.H + 1))
                            region_H = new.H
                        else:
                            out.write("\x1b7\x1b[%d;%dr\x1b8" % (new.H + 1, size[1]))
                        write_state(flag, new.H, parent)
                    first = False
                if rend is None or paused or os.path.exists(flag):
                    time.sleep(0.25)
                    continue
                t1 = time.time()
                out.write(rend.render(t1 - t0))
                dt = 1.0 / max(2, min(60, as_int(cfg["fps"], 16))) - (time.time() - t1)
                time.sleep(max(0.01, dt))
            except OSError as e:
                if e.errno in (errno.EIO, errno.EBADF, errno.ENXIO):
                    break
                log_error()
                time.sleep(0.5)
            except Exception:
                log_error()
                time.sleep(0.5)
    finally:
        try:
            os.remove(flag + ".state")
        except OSError:
            pass
        try:
            out.write("\x1b[r")
        except Exception:
            pass
    return 0

def cmd_height(cfg):
    cols, rows = term_size()
    H = 0
    term = os.environ.get("TERM", "dumb")
    if term not in ("linux", "dumb", "") and not os.environ.get("TERMFX_DISABLE"):
        try:
            lay = build_layout(cfg, cols, rows)
            H = lay.H if lay else 0
        except Exception:
            log_error()
    pm = "never" if (cfg["pause"].strip().lower() == "never") else "auto"
    print(H, rows, cols, pm)
    return 0

def cmd_preview(cfg, secs):
    cols, rows = term_size()
    lay = build_layout(cfg, cols, rows, force=True)
    rend = Renderer(cfg, lay)
    out = Out()
    fdin, old = None, None
    try:
        import termios, tty
        fdin = sys.stdin.fileno()
        old = termios.tcgetattr(fdin)
        tty.setcbreak(fdin)
    except Exception:
        fdin = None
    out.write("\x1b[?1049h\x1b[?25l\x1b[2J")
    t0 = time.time()
    fps = max(2, min(60, as_int(cfg["fps"], 16)))
    hint = "art: %s   effect: %s   palette: %s   -   press any key to exit" % (
        os.path.basename(lay.path or "builtin"), rend.effect_name, cfg["palette"])
    try:
        while time.time() - t0 < secs:
            out.write(rend.render(time.time() - t0, top=1, save=False))
            out.write("\x1b[%d;1H\x1b[2m%s\x1b[0m\x1b[K" % (min(rows, lay.H + 4), hint))
            if fdin is not None:
                r, _, _ = select.select([fdin], [], [], 1.0 / fps)
                if r:
                    os.read(fdin, 64)
                    break
            else:
                time.sleep(1.0 / fps)
    finally:
        out.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        if old is not None:
            import termios
            termios.tcsetattr(fdin, termios.TCSADRAIN, old)
    return 0

def cmd_art_info(cfg, name):
    if name:
        cfg["art"] = name
    path = resolve_art(cfg["art"])
    print("name   :", cfg["art"])
    print("file   :", path or "(not found, using built-in fallback)")
    if not path:
        return 1
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = parse_art(fh.read())
    if not src:
        print("empty  : yes - the file has no visible content")
        return 1
    print("frames :", len(src))
    print("source : %d cols x %d rows" % (max(len(r) for f in src for r in f), max(len(f) for f in src)))
    cols, rows = term_size()
    if cols:
        lay = build_layout(cfg, cols, rows, force=True)
        print("fitted : %d cols x %d rows  (terminal %dx%d, header height %d)" % (lay.aw, lay.ah, cols, rows, lay.H))
    return 0

def cmd_distro_logo(name):
    ff = shutil.which("fastfetch")
    if not ff:
        return 1
    for base in ([ff, "-s", "Break", "--pipe", "false"], [ff, "-s", "Break"], [ff, "--structure", "Break", "--pipe", "false"]):
        argv = base + (["-l", name] if name else [])
        txt = ANSI_RE.sub("", _run(argv))
        lines = [l.rstrip() for l in txt.split("\n")]
        while lines and not lines[-1].strip():
            lines.pop()
        if len([l for l in lines if l.strip()]) >= 3:
            print("\n".join(lines))
            return 0
    return 1

def cmd_doctor(cfg):
    cols, rows = term_size()
    print("termfx-engine", VERSION, "| python", sys.version.split()[0])
    print("config     :", CONF_FILE, "(exists)" if os.path.exists(CONF_FILE) else "(missing)")
    print("art dir    :", ART_DIR, "-", len(glob.glob(os.path.join(ART_DIR, "*.txt"))), "files")
    print("terminal   : %dx%d  TERM=%s  COLORTERM=%s" % (cols, rows, os.environ.get("TERM"), os.environ.get("COLORTERM")))
    print("truecolor  :", truecolor_on(cfg), "| utf-8 locale:", UTF8)
    print("min size   : %sx%s (animation hidden below this)" % (cfg["min_cols"], cfg["min_rows"]))
    for t in ("fastfetch", "neofetch", "starship", "eza", "bat", "batcat", "fzf", "chafa", "jp2a", "figlet"):
        print("%-11s: %s" % (t, shutil.which(t) or "-"))
    try:
        lay = build_layout(cfg, cols, rows)
        if lay:
            print("header     : %d rows, art %dx%d, %d frame(s), info %d lines" % (
                lay.H, lay.aw, lay.ah, len(lay.frames), len(lay.info)))
        elif not as_bool(cfg["enabled"]):
            print("header     : disabled (run: termfx on)")
        elif cols < as_int(cfg["min_cols"], 80) or rows < as_int(cfg["min_rows"], 24):
            print("header     : hidden - resize terminal to at least %sx%s (now %dx%d)" % (
                cfg["min_cols"], cfg["min_rows"], cols, rows))
            print("tip        : or lower the bar with  termfx set min_cols 60  &&  termfx set min_rows 20")
        else:
            print("header     : inactive (check art / config)")
    except Exception:
        print("header     : ERROR (see %s)" % os.path.join(CACHE_DIR, "error.log"))
        log_error()
    return 0

def cmd_effect_info(name):
    """Show detailed info about a specific effect."""
    name = (name or "").strip().lower()
    if not name or name == "list":
        for e in EFFECTS:
            print("%-14s %s" % (e, EFFECT_DESC.get(e, "")))
        return 0
    if name not in EFFECTS:
        print("unknown effect '%s'" % name, file=sys.stderr)
        return 1
    print("name      : %s" % name)
    print("desc      : %s" % EFFECT_DESC.get(name, ""))
    print("palette   : %s (auto-recommended)" % EFFECT_PALETTE.get(name, "catppuccin"))
    pal_stops = PALETTES.get(EFFECT_PALETTE.get(name, "catppuccin"), "").split()
    print("colours   : %s" % " ".join("#" + s for s in pal_stops))
    return 0

def cmd_palette_show(name):
    """Show palette colours with ANSI rendering."""
    name = (name or "").strip().lower()
    if not name or name == "list":
        print("\n".join(sorted(PALETTES)))
        return 0
    if name not in PALETTES:
        print("unknown palette '%s'" % name, file=sys.stderr)
        return 1
    stops = PALETTES[name].split()
    print("palette : %s (%d colours)" % (name, len(stops)))
    print("hex     : %s" % " ".join("#" + s for s in stops))
    # render colour blocks
    bar = ""
    for s in stops:
        r, g, b = hex_rgb(s)
        bar += "\x1b[48;2;%d;%d;%dm  " % (r, g, b)
    bar += "\x1b[0m"
    if sys.stdout.isatty():                 # colour swatches only on a terminal
        print("preview : %s" % bar)
    # gradient test strip
    lut = build_lut(stops, 64)
    grad = ""
    for r, g, b in lut:
        grad += "\x1b[48;2;%d;%d;%dm " % (r, g, b)
    grad += "\x1b[0m"
    if sys.stdout.isatty():                 # the strip is made of colour codes: skip it when piped
        print("gradient: %s" % grad)
    # used by effects
    used_by = [e for e, p in EFFECT_PALETTE.items() if p == name]
    if used_by:
        print("used by : %s" % ", ".join(used_by))
    return 0

def cmd_palette_catalog():
    """List every palette with its number of stops and exact colour values (fits 80 columns)."""
    print("Palettes: %d" % len(PALETTES))
    w = max(len(n) for n in PALETTES) + 1
    for name in sorted(PALETTES):
        stops = PALETTES[name].split()
        print("%-*s %d  %s" % (w, name, len(stops), " ".join("#" + s for s in stops)))
    return 0

def cmd_info_items():
    """List available info panel items and their status."""
    items = [
        ("user", "Username", "builtin"),
        ("hostname", "Hostname", "builtin"),
        ("os", "Operating System", "builtin"),
        ("kernel", "Kernel version", "builtin"),
        ("uptime", "System uptime", "builtin"),
        ("shell", "Active shell", "builtin"),
        ("terminal", "Terminal emulator", "builtin"),
        ("desktop", "Desktop environment", "builtin"),
        ("cpu", "CPU model", "builtin"),
        ("memory", "RAM usage", "builtin"),
        ("disk", "Disk usage", "fastfetch"),
        ("gpu", "GPU info", "fastfetch"),
        ("packages", "Installed packages", "fastfetch"),
        ("wm", "Window manager", "fastfetch"),
        ("theme", "GTK/Qt theme", "fastfetch"),
        ("icons", "Icon theme", "fastfetch"),
        ("font", "Default font", "fastfetch"),
        ("battery", "Battery status", "fastfetch"),
        ("local_ip", "Local IP", "fastfetch"),
        ("public_ip", "Public IP", "fastfetch"),
        ("date", "Current date/time", "fastfetch"),
        ("music", "Currently playing", "fastfetch"),
        ("weather", "Weather (custom cmd)", "custom"),
        ("custom", "User-defined command output", "custom"),
    ]
    print("%-12s %-26s %s" % ("ITEM", "DESCRIPTION", "SOURCE"))
    print("-" * 62)
    for name, desc, src in items:
        print("%-12s %-26s %s" % (name, desc, src))
    print()
    print("Configure: termfx info-rows item1,item2,... | termfx set info_cmd 'your-cmd'")
    return 0

def main(argv):
    args = argv[1:]
    while args and args[0].startswith("--"):
        a = args.pop(0)
        if a == "--set" and args:
            k, _, v = args.pop(0).partition("=")
            OVERRIDES[k.strip().lower()] = v
        else:
            print(__doc__)
            return 2
    cmd = args.pop(0) if args else "help"
    cfg = load_config()
    if cmd == "height":
        return cmd_height(cfg)
    if cmd == "run" and len(args) >= 2:
        return cmd_run(args[0], int(args[1]))
    if cmd == "preview":
        return cmd_preview(cfg, as_float(args[0], 6.0) if args else 6.0)
    if cmd == "prepare":
        cols, rows = term_size()
        build_layout(cfg, cols or 120, rows or 40, force=True)
        return 0
    if cmd == "art-info":
        return cmd_art_info(cfg, args[0] if args else "")
    if cmd == "list":
        what = args[0] if args else "effects"
        if what == "effects":
            for e in EFFECTS:
                palette = EFFECT_PALETTE.get(e, "catppuccin")
                print("%-14s %-34s palette: %s" % (e, EFFECT_DESC.get(e, ""), palette))
        elif what == "palettes":
            print("\n".join(sorted(PALETTES)))
        elif what == "effect-menu":
            for e in EFFECTS:
                print("%s\t%s\t%s" % (e, EFFECT_DESC.get(e, ""), EFFECT_PALETTE.get(e, "catppuccin")))
        elif what == "palette-menu":
            for name in sorted(PALETTES):
                stops = PALETTES[name].split()
                print("%s %d %s" % (name, len(stops), " ".join(stops)))
        elif what in ("palette-details", "palette-info"):
            return cmd_palette_catalog()
        elif what == "art":
            print("\n".join(sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ART_DIR, "*.txt")))))
        elif what == "info-items":
            return cmd_info_items()
        return 0
    if cmd == "effect-info":
        return cmd_effect_info(args[0] if args else "")
    if cmd == "palette-show":
        return cmd_palette_show(args[0] if args else "")
    if cmd == "info":
        print("\n".join(get_info(cfg)))
        return 0
    if cmd == "info-colors-preview":
        cols = _info_palette_colors(cfg)
        print("info_colors = %s" % cfg.get("info_colors", "auto"))
        print("colours   : %s" % " ".join("\x1b[38;2;%sm#\x1b[0m" % c for c in cols))
        bar = "".join("\x1b[48;2;%sm  \x1b[0m" % c for c in cols)
        print("preview   : %s" % bar)
        return 0
    if cmd == "distro-logo":
        return cmd_distro_logo(args[0] if args else "")
    if cmd == "doctor":
        return cmd_doctor(cfg)
    if cmd == "version":
        print(VERSION)
        return 0
    print(__doc__)
    return 0 if cmd in ("help", "-h", "--help") else 2
