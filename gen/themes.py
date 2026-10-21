#!/usr/bin/env python3
"""termfx-themes - generates starship + fastfetch + terminal snippets from config.

Reads ~/.config/termfx/config :  theme, prompt_style, prompt_char, prompt_lines,
                                 clock, clock_format, info_style, info_rows
Your own colour themes: ~/.config/termfx/themes/NAME.json (see `termfx theme new`).
Usage: termfx-themes [--list themes|prompts|infos|rows|starship]   (CONF_DIR env overrides the dir)
"""
import json, os, re, sys, glob

CONF = os.environ.get("CONF_DIR") or os.path.join(
    os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "termfx")

# ------------------------------------------------------------------ colour themes
KEYS = "dark dim text pink mauve blue sky teal green yellow peach red".split()
def T(s): return dict(zip(KEYS, ["#" + x for x in s.split()]))
THEMES = {
 "catppuccin": T("1e1e2e 585b70 cdd6f4 f5c2e7 cba6f7 89b4fa 74c7ec 94e2d5 a6e3a1 f9e2af fab387 f38ba8"),
 "tokyonight": T("1a1b26 565f89 c0caf5 ff9ac1 bb9af7 7aa2f7 7dcfff 73daca 9ece6a e0af68 ff9e64 f7768e"),
 "dracula":    T("282a36 6272a4 f8f8f2 ff79c6 bd93f9 82aaff 8be9fd 8be9fd 50fa7b f1fa8c ffb86c ff5555"),
 "nord":       T("2e3440 4c566a d8dee9 b48ead b48ead 81a1c1 88c0d0 8fbcbb a3be8c ebcb8b d08770 bf616a"),
 "gruvbox":    T("282828 665c54 ebdbb2 d3869b d3869b 83a598 8ec07c 8ec07c b8bb26 fabd2f fe8019 fb4934"),
 "rosepine":   T("191724 6e6a86 e0def4 ebbcba c4a7e7 7fb4ca 9ccfd8 9ccfd8 95b1ac f6c177 ea9a97 eb6f92"),
 "onedark":    T("21252b 5c6370 abb2bf c678dd c678dd 61afef 56b6c2 56b6c2 98c379 e5c07b d19a66 e06c75"),
 "mono":       T("111111 555555 dddddd eeeeee cccccc bbbbbb aaaaaa 999999 dddddd c8c8c8 b0b0b0 ffffff"),
}
for p in glob.glob(os.path.join(CONF, "themes", "*.json")):      # user themes
    try:
        d = json.load(open(p, encoding="utf-8"))
        base = dict(THEMES.get(d.get("base", "catppuccin"), THEMES["catppuccin"]))
        base.update({k: v if v.startswith("#") else "#" + v for k, v in d.items() if k in KEYS})
        THEMES[os.path.splitext(os.path.basename(p))[0]] = base
    except Exception as e:
        print("termfx: bad theme %s: %s" % (p, e), file=sys.stderr)

# ------------------------------------------------------------------ prompt shapes
G = chr
SHAPES = {   # name: (left cap, right cap, description)
 "pills":   (G(0xe0b6), G(0xe0b4), "rounded pills"),
 "blocks":  ("", "", "flat colour blocks"),
 "sharp":   (G(0xe0b2), G(0xe0b0), "powerline arrows"),
 "slant":   (G(0xe0ba), G(0xe0b8), "slanted edges"),
 "minimal": (None, None, "one clean line, no blocks"),
 "plain":   (None, None, "no icons/glyphs (works in any font)"),
}
INFOS = {"boxed": "framed panel", "clean": "no frame, coloured keys", "compact": "boxed, fewer rows",
         "minimal": "just name + value"}

# Starship modules supported by the prompt builder. Optional modules are off by default.
STARSHIP_MODULES = "username hostname localip shlvl singularity kubernetes nats directory vcsh fossil_branch fossil_metrics git_branch git_commit git_state git_metrics git_status hg_branch hg_state pijul_channel docker_context package bun c cmake cobol cpp daml dart deno dotnet elixir elm erlang fennel fortran gleam golang gradle haskell haxe helm java julia kotlin lua maven mojo nim nodejs ocaml odin opa perl php pulumi purescript python quarto raku rlang red ruby rust scala solidity swift terraform typst vlang vagrant xmake zig buf guix_shell nix_shell conda pixi meson spack memory_usage aws gcloud openstack azure direnv env_var mise crystal sudo cmd_duration line_break jobs battery time status container netns os shell".split()
DEFAULT_STARSHIP_MODULES = "os username hostname directory git_branch git_status python nodejs rust golang java docker_context cmd_duration status time".split()
STARSHIP_MODULE_PRESETS = {
    "balanced": DEFAULT_STARSHIP_MODULES,
    "minimal": "username directory git_branch git_status cmd_duration status time".split(),
    "developer": ("os username hostname directory git_branch git_status python nodejs rust golang java docker_context cmd_duration status time "
                  "bun c cmake cpp dart deno dotnet elixir elm erlang gradle haskell julia kotlin lua perl php ruby scala swift package").split(),
    "cloud": ("os username hostname directory git_branch git_status python nodejs rust golang java docker_context cmd_duration status time "
              "aws azure gcloud kubernetes openstack terraform nix_shell").split(),
    "server": "username hostname localip shlvl directory git_branch git_status docker_context aws azure gcloud kubernetes cmd_duration jobs sudo status time shell".split(),
    "full": STARSHIP_MODULES,
}
STARSHIP_THEMES = {
    "terminal-match": ("Terminal Match", "", "", "balanced"),
    "catppuccin-mocha": ("Catppuccin Mocha", "catppuccin", "pills", "balanced"),
    "tokyo-night": ("Tokyo Night", "tokyonight", "sharp", "balanced"),
    "nord-frost": ("Nord Frost", "nord", "blocks", "balanced"),
    "dracula-night": ("Dracula Night", "dracula", "slant", "balanced"),
    "gruvbox-retro": ("Gruvbox Retro", "gruvbox", "slant", "balanced"),
    "rose-pine": ("Rosé Pine", "rosepine", "minimal", "minimal"),
    "one-dark": ("One Dark", "onedark", "blocks", "balanced"),
    "mono-ink": ("Mono Ink", "mono", "minimal", "minimal"),
    "developer-forge": ("Developer Forge", "tokyonight", "sharp", "developer"),
    "cloud-ops": ("Cloud Ops", "nord", "blocks", "cloud"),
    "server-console": ("Server Console", "mono", "minimal", "server"),
    "neon-cyberpunk": ("Neon Cyberpunk", "cyberpunk", "pills", "developer"),
    "solarized-terminal": ("Solarized Terminal", "solarized", "sharp", "balanced"),
    "plain-clean": ("Plain Clean", "mono", "plain", "minimal"),
}
THEMES["cyberpunk"] = T("090b1a 394064 e9f7ff f700ff 9d4edd 00e5ff 00f5d4 8affc1 39ff14 f9f871 ff8c42 ff3864")
THEMES["solarized"] = T("002b36 586e75 93a1a1 cb4b16 6c71c4 268bd2 2aa198 2aa198 859900 b58900 cb4b16 dc322f")

# ------------------------------------------------------------------ config
def read_conf():
    c = {}
    try:
        for line in open(os.path.join(CONF, "config"), encoding="utf-8"):
            m = re.match(r"\s*([A-Za-z_]+)\s*=\s*(.*?)\s*(?:\s#.*)?$", line)
            if not m: continue
            v = m.group(2)
            q = re.match(r"""(["'])(.*?)\1""", line.split("=", 1)[1].strip())   # "quoted value" keeps # and spaces
            c[m.group(1)] = q.group(2) if q else v
    except OSError: pass
    return c

ROWS = {  # name: (icon, fastfetch type, colour role, extra)
 "user": (0xf007, "title", "pink", {"format": "{user-name}"}),
 "hname": (0xf01c5, "title", "mauve", {"format": "{host-name}"}),
 "uptime": (0xf0150, "uptime", "blue", {}), "distro": (0xf303, "os", "sky", {}),
 "kernel": (0xf17c, "kernel", "teal", {}), "wm": (0xf2d0, "wm", "green", {}),
 "desktop": (0xf01c4, "de", "yellow", {}), "term": (0xf120, "terminal", "peach", {}),
 "shell": (0xf489, "shell", "red", {}), "cpu": (0xf035b, "cpu", "pink", {}),
 "gpu": (0xf0379, "gpu", "mauve", {}), "disk": (0xf0249, "disk", "blue", {"folders": "/"}),
 "memory": (0xf2db, "memory", "sky", {}), "packages": (0xf487, "packages", "teal", {}),
 "battery": (0xf0079, "battery", "green", {}), "local_ip": (0xf0a5f, "localip", "yellow", {}),
 "colors": (0xf53f, "colors", "blue", {}),
}
DEFAULT_ROWS = "user hname uptime distro kernel wm desktop term shell cpu disk memory"
COMPACT_ROWS = "user distro kernel wm shell cpu memory"

# ------------------------------------------------------------------ fetch presets
FETCH_PRESETS = {
  "classic":    {"rows": "user hname uptime distro kernel wm desktop term shell cpu disk memory",
                 "style": "boxed", "desc": "the default termfx look — boxed, full system info"},
  "compact":    {"rows": "user distro kernel shell cpu memory",
                 "style": "compact", "desc": "few rows, tight box, quick glance"},
  "minimal":    {"rows": "distro kernel uptime",
                 "style": "minimal", "desc": "barely-there — just 3 key facts, no frame"},
  "clean":      {"rows": "user hname uptime distro kernel wm term shell cpu gpu disk memory",
                 "style": "clean", "desc": "no box, colour-coded keys, airy spacing"},
  "full":       {"rows": "user hname uptime distro kernel wm desktop term shell cpu gpu disk memory packages battery local_ip",
                 "style": "boxed", "desc": "everything — every available field in a box"},
  "gamer":      {"rows": "distro kernel cpu gpu memory disk",
                 "style": "boxed", "desc": "hardware focus — CPU, GPU, RAM, storage"},
  "server":     {"rows": "user hname uptime distro kernel disk memory local_ip",
                 "style": "clean", "desc": "sysadmin — uptime, disk, IP, no desktop cruft"},
  "developer":  {"rows": "user distro shell term kernel wm cpu memory packages",
                 "style": "boxed", "desc": "dev workhorse — tooling, packages, environment"},
  "aesthetic":  {"rows": "user hname uptime distro kernel term shell memory",
                 "style": "clean", "desc": "soft minimal — colour keys, no borders"},
  "hybridfetch": {"rows": "user hname uptime distro kernel wm term shell cpu gpu disk memory colors",
                 "style": "boxed", "desc": "includes colour swatches at the bottom"},
  "ultra":      {"rows": "user hname uptime distro kernel wm desktop term shell cpu gpu disk memory packages battery local_ip colors",
                 "style": "boxed", "desc": "max data + colour swatches, the full spread"},
}

def rgb(h): h = h.lstrip("#"); return "%d;%d;%d" % tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--dump":
        print(json.dumps({"base": sys.argv[2], **THEMES[sys.argv[2]]}, indent=2)); return
    if len(sys.argv) > 2 and sys.argv[1] == "--list":
        w = sys.argv[2]
        if w == "themes":  print("\n".join(sorted(THEMES)))
        elif w == "prompts": print("\n".join("%-9s %s" % (k, v[2]) for k, v in SHAPES.items()))
        elif w == "infos":  print("\n".join("%-9s %s" % (k, v) for k, v in INFOS.items()))
        elif w == "starship": print("\n".join("%-22s %s" % (k, v[0]) for k, v in STARSHIP_THEMES.items()))
        elif w == "rows":   print(" ".join(k for k in ROWS if k != "colors"))
        elif w == "fetch":
            for k, v in FETCH_PRESETS.items():
                print("%-13s %s" % (k, v["desc"]))
        return
    if len(sys.argv) > 2 and sys.argv[1] == "--starship-modules":
        profile = STARSHIP_THEMES.get(sys.argv[2])
        if profile:
            print(" ".join(STARSHIP_MODULE_PRESETS[profile[3]]))
            return
        print("unknown Starship theme: " + sys.argv[2], file=sys.stderr); sys.exit(2)
    if len(sys.argv) > 2 and sys.argv[1] == "--starship-style":
        profile = STARSHIP_THEMES.get(sys.argv[2])
        if profile:
            print(profile[2])
            return
        print("unknown Starship theme: " + sys.argv[2], file=sys.stderr); sys.exit(2)
    cf = read_conf()
    theme = cf.get("theme", "catppuccin"); P = THEMES.get(theme) or THEMES["catppuccin"]
    style = cf.get("prompt_style", "pills"); style = style if style in SHAPES or style == "custom" else "pills"
    char = re.sub(r"['\n\r]", "", cf.get("prompt_char") or "") or "❯"   # ' would break starship's TOML literal strings
    lines = 1 if cf.get("prompt_lines", "2") == "1" else 2
    clock = cf.get("clock", "true").lower() != "false"
    tfmt = cf.get("clock_format") or "%H:%M"
    info = cf.get("info_style", "boxed"); info = info if info in INFOS else "boxed"
    os.makedirs(CONF, exist_ok=True)
    write_fastfetch(P, info, cf)
    starship_theme = cf.get("starship_theme", "terminal-match")
    if starship_theme not in STARSHIP_THEMES: starship_theme = "terminal-match"
    profile = STARSHIP_THEMES[starship_theme]
    starship_palette = THEMES.get(profile[1], P)
    starship_style = profile[2] or style
    active_cf = dict(cf)
    if not active_cf.get("starship_modules"):
        active_cf["starship_modules"] = " ".join(STARSHIP_MODULE_PRESETS[profile[3]])
    plain_style = starship_style if starship_style in SHAPES else "plain"
    write_starship(starship_palette, plain_style, char, lines, clock, tfmt,
                   os.path.join(CONF, "starship-plain.toml"), plain=True, cf=active_cf)
    if style != "custom" or starship_theme != "terminal-match":
        # Keep a hand-edited prompt untouched until a named Starship theme is explicitly chosen.
        write_starship(starship_palette, starship_style, char, lines, clock, tfmt,
                       os.path.join(CONF, "starship.toml"), plain=False, cf=active_cf)
    theme_dir = os.path.join(CONF, "starship-themes")
    os.makedirs(theme_dir, exist_ok=True)
    for name, entry in STARSHIP_THEMES.items():
        theme_palette = THEMES.get(entry[1], P)
        theme_style = entry[2] or (style if style in SHAPES else "pills")
        theme_cf = dict(cf)
        theme_cf["starship_modules"] = " ".join(STARSHIP_MODULE_PRESETS[entry[3]])
        write_starship(theme_palette, theme_style, char, lines, clock, tfmt,
                       os.path.join(theme_dir, name + ".toml"), plain=False, cf=theme_cf)
    write_terms(P)

# ------------------------------------------------------------------ fastfetch
def write_fastfetch(P, info, cf):
    preset_name = (cf.get("fetch_preset") or "").strip()
    if preset_name and preset_name in FETCH_PRESETS:
        preset = FETCH_PRESETS[preset_name]
        names = [n for n in preset["rows"].split() if n in ROWS and n != "colors"]
        info = preset["style"]
    else:
        names = (cf.get("info_rows") or "").replace(",", " ").split()
        names = [n for n in names if n in ROWS and n != "colors"] or (COMPACT_ROWS if info == "compact" else DEFAULT_ROWS).split()
    col = lambda r: "1;38;2;" + rgb(P[r])
    boxed = info in ("boxed", "compact")
    def key(n):
        ic, nm = chr(ROWS[n][0]), n.ljust(7)
        if boxed: return "│ %s %s │ " % (ic, nm)
        if info == "clean": return "%s %s  " % (ic, nm)
        return "%s  " % n.ljust(8)
    def row(n, **kw):
        ic, typ, role, extra = ROWS[n]
        d = {"type": typ, "key": key(n), "keyColor": col(role), "outputColor": col(role)}
        if info == "minimal": d["outputColor"] = "38;2;" + rgb(P["text"])
        d.update(extra); d.update(kw); return d
    border = lambda t, r: {"type": "custom", "format": t, "outputColor": col(r)}
    w = 11
    mods = [border("╭" + "─" * w + "╮", "blue")] if boxed else []
    mods += [row(n) for n in names]
    if boxed: mods.append(border("├" + "─" * w + "┤", "mauve"))
    if info != "minimal":
        mods.append({"type": "colors", "key": key("colors") if info != "clean" else key("colors"),
                     "keyColor": col("blue"), "symbol": "circle"})
    if boxed: mods.append(border("╰" + "─" * w + "╯", "pink"))
    cfg = {"$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
           "logo": {"type": "none"}, "display": {"separator": ""}, "modules": mods}
    with open(os.path.join(CONF, "fastfetch.jsonc"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ------------------------------------------------------------------ starship
def write_starship(P, style, char, lines, clock, tfmt, path, plain, cf):
    glyphless = plain or style == "plain"
    I = lambda cp: "" if glyphless else chr(cp)
    L, R, _ = SHAPES[style]
    d = P["dark"]; dim = P["dim"]
    def seg(c, body, trail=" "):
        if glyphless:
            if style == "pills": return "[( %s )](bg:%s fg:%s bold)%s" % (body, c, d, trail)
            if style == "blocks": return "[ %s ](bg:%s fg:%s bold)%s" % (body, c, d, trail)
            if style == "sharp": return "[› %s](bold %s)%s" % (body, c, trail)
            if style == "slant": return "[/ %s /](bold %s)%s" % (body, c, trail)
        if style in ("minimal", "plain"): return "[%s](bold %s)%s" % (body.strip(), c, trail)
        return "[%s](fg:%s)[ %s ](bg:%s fg:%s bold)[%s](fg:%s)%s" % (L, c, body, c, d, R, c, trail) if L or R \
            else "[ %s ](bg:%s fg:%s bold)%s" % (body, c, d, trail)
    def mod(name, c, body, extra=""):
        return "[%s]\n%sformat = '%s'\n\n" % (name, extra, seg(c, body))
    def gstat(c):
        if style in ("minimal", "plain"): return "([$all_status$ahead_behind](bold %s) )" % c
        return "(%s)" % seg(c, "$all_status$ahead_behind")
    # characters
    if len(char) == 1: ok = "".join("[%s](bold %s)" % (char, P[r]) for r in ("pink", "mauve", "blue")); er = "[%s](bold %s)" % (char * 3, P["red"])
    else: ok = "[%s](bold %s)" % (char, P["mauve"]); er = "[%s](bold %s)" % (char, P["red"])
    if glyphless: ok, er = "[>](bold %s)" % P["green"], "[>](bold %s)" % P["red"]
    two = lines == 2 and style not in ("minimal", "plain")
    selected = (cf.get("starship_modules") or " ".join(DEFAULT_STARSHIP_MODULES)).replace(",", " ").split()
    modules = set() if selected == ["none"] else set(selected)
    if plain:
        order = "username hostname directory git_branch git_status cmd_duration status".split()
        order += [m for m in STARSHIP_MODULES if m in modules and m not in DEFAULT_STARSHIP_MODULES]
    elif style == "minimal":
        order = "directory git_branch git_status cmd_duration status".split()
        order += [m for m in STARSHIP_MODULES if m in modules and m not in DEFAULT_STARSHIP_MODULES]
    else:
        order = STARSHIP_MODULES
    left = "".join("$" + m for m in order if m in modules and m != "time")
    right_clock = clock and "time" in modules
    right_prompt = cf.get("starship_right_prompt", "false").lower() in ("true", "1", "yes", "on")
    right = "" if right_prompt else ("$fill$time" if right_clock and two else ("$time" if right_clock and style != "minimal" else ""))
    top = ("[╭─](bold %s)" % dim) if two else ""
    fmt = top + left + right + (("\n[╰─](bold %s)$character" % dim) if two else "$character")
    def enabled(key, default=True):
        return cf.get(key, str(default)).lower() not in ("false", "0", "no", "off")
    def number(key, default, low, high):
        try: return max(low, min(high, int(cf.get(key, default))))
        except (TypeError, ValueError): return int(default)
    def quoted(value): return json.dumps(str(value), ensure_ascii=False)
    t = ("add_newline = %s\nscan_timeout = %d\ncommand_timeout = %d\nfollow_symlinks = %s\nformat = \"\"\"\n%s\"\"\"\n\n" % (
        str(enabled("starship_newline")).lower(), number("starship_scan_timeout", "30", 1, 5000),
        number("starship_command_timeout", "500", 1, 60000), str(enabled("starship_follow_symlinks")).lower(), fmt))
    if right_prompt and right_clock:
        t += "right_format = '$time'\n\n"
    if not glyphless:
        t += mod("os", P["mauve"], "$symbol", "disabled = false\n")
    else:
        t += "[os]\ndisabled = false\nformat = '$name '\n\n"
    t += "[username]\nshow_always = %s\n" % str(enabled("starship_username_always")).lower()
    t += "format = '%s'\n\n" % seg(P["blue"], I(0xf007) + (" " if not plain else "") + "$user")
    t += "[hostname]\nssh_only = %s\nformat = '%s'\n\n" % (str(enabled("starship_ssh_only")).lower(), seg(P["pink"], I(0xf109) + (" " if not plain else "") + "$hostname"))
    t += ("[directory]\nhome_symbol = '~'\ntruncation_length = %d\ntruncation_symbol = '…/'\ntruncate_to_repo = %s\n"
          "read_only = ' %s'\nformat = '%s'\n\n" % (number("starship_directory_length", "3", 0, 20),
          str(enabled("starship_truncate_to_repo")).lower(), I(0xf033e) or "ro",
          seg(P["sky"], I(0xf07b) + (" " if not plain else "") + "$path$read_only")))
    if not glyphless:
        t += "[directory.substitutions]\n" + "".join("'%s' = '%s %s'\n" % (k, chr(cp), k) for k, cp in
             [("Documents", 0xf0219), ("Downloads", 0xf019), ("Pictures", 0xf03e), ("Videos", 0xf03d),
              ("Music", 0xf075a), ("Desktop", 0xf108), (".config", 0xe5fc)]) + "\n"
    t += "[git_branch]\nsymbol = %s\nformat = '%s'\nalways_show_remote = %s\n" % (
        quoted(cf.get("starship_git_symbol") or (I(0xe0a0) or "git:")), seg(P["green"], "$symbol $branch"),
        str(enabled("starship_git_remote")).lower())
    branch_length = number("starship_git_branch_length", "0", 0, 200)
    if branch_length: t += "truncation_length = %d\n" % branch_length
    t += "\n"
    t += "[git_status]\nformat = '%s'\n" % gstat(P["peach"])
    for key, default in (("conflicted", "⚡"), ("ahead", "⇡${count}"), ("behind", "⇣${count}"),
                         ("diverged", "⇕⇡${ahead_count}⇣${behind_count}"), ("untracked", "?${count}"),
                         ("stashed", "≡"), ("modified", "!${count}"), ("staged", "+${count}"),
                         ("renamed", "»"), ("deleted", "✘${count}")):
        t += "%s = %s\n" % (key, quoted(cf.get("starship_git_" + key, default)))
    t += "\n"
    if not glyphless:
        for m, c, cp in (("python", "yellow", 0xe73c), ("nodejs", "green", 0xe718), ("rust", "red", 0xe7a8),
                         ("golang", "teal", 0xe627), ("java", "peach", 0xe256)):
            t += "[%s]\nformat = '%s'\n\n" % (m, seg(P[c], chr(cp) + " $version"))
        t += "[docker_context]\nformat = '%s'\n\n" % seg(P["sky"], chr(0xf308) + " $context")
    else:
        for m, c in (("python", "yellow"), ("nodejs", "green"), ("rust", "red"),
                     ("golang", "teal"), ("java", "peach")):
            t += "[%s]\nformat = '%s'\n\n" % (m, seg(P[c], "$version"))
        t += "[docker_context]\nformat = '%s'\n\n" % seg(P["sky"], "$context")
    t += "[cmd_duration]\nmin_time = %d\nformat = '%s'\n\n" % (number("starship_duration_min", "2000", 0, 600000), seg(P["yellow"], I(0xf051f) + (" " if not plain else "took ") + "$duration"))
    t += "[status]\ndisabled = false\nformat = '%s'\n\n" % seg(P["red"], I(0xf00d) + (" " if not plain else "exit ") + "$status")
    t += "[fill]\nsymbol = '%s'\nstyle = '%s'\n\n" % ("·" if not glyphless else ".", dim)
    tl = seg(P["pink"], I(0xf017) + (" " if not plain else "") + "$time", trail="")
    safe_tfmt = re.sub(r"['\n\r]", "", cf.get("starship_time_format") or tfmt)
    t += "[time]\ndisabled = %s\ntime_format = %s\nformat = '%s'\n\n" % (str(not right_clock).lower(), quoted(safe_tfmt), tl)
    t += "[character]\nsuccess_symbol = '%s'\nerror_symbol = '%s'\n" % (ok, er)
    fill = re.sub(r"['\n\r]", "", cf.get("starship_fill_symbol") or ("·" if not glyphless else "."))
    t = t.replace("symbol = '%s'\nstyle = '%s'\n\n" % ("·" if not glyphless else ".", dim),
                  "symbol = %s\nstyle = '%s'\n\n" % (quoted(fill), dim))
    for m in order:
        if m in modules and m not in DEFAULT_STARSHIP_MODULES and m not in ("fill", "character"):
            t += "[%s]\ndisabled = false\n\n" % m
    with open(path, "w", encoding="utf-8") as f: f.write(t)

# ------------------------------------------------------------------ terminal snippets
def write_terms(P):
    pal = [P["dim"], P["red"], P["green"], P["yellow"], P["blue"], P["pink"], P["teal"], P["text"]]
    pal = pal + pal
    with open(os.path.join(CONF, "ghostty.conf"), "w", encoding="utf-8") as f:
        f.write("# termfx look for Ghostty (paste into ~/.config/ghostty/config)\n"
                "font-family = JetBrainsMono Nerd Font\nfont-size = 12\n"
                "background = %s\nforeground = %s\nbackground-opacity = 0.85\n"
                "cursor-style = block\ncursor-style-blink = false\n"
                "window-padding-x = 16\nwindow-padding-y = 12\nwindow-width = 120\nwindow-height = 40\n"
                % (P["dark"][1:], P["text"][1:]))
        for i, c in enumerate(pal): f.write("palette = %d=%s\n" % (i, c))
    with open(os.path.join(CONF, "kitty.conf"), "w", encoding="utf-8") as f:
        f.write("# termfx look for kitty\nfont_family JetBrainsMono Nerd Font\nfont_size 12.0\n"
                "background %s\nforeground %s\nbackground_opacity 0.85\n"
                "cursor_shape block\ncursor_blink_interval 0\nwindow_padding_width 12 16\n"
                "initial_window_width 120c\ninitial_window_height 40c\n" % (P["dark"], P["text"]))
        for i, c in enumerate(pal): f.write("color%d %s\n" % (i, c))

main()
