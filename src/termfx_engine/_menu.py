"""Pretty, installer-style menus: termfx effect list | palette list | palette colors | info-colors list.

Numbered rows, colour swatches, descriptions and a marker on the value that is in use.
When stdout is not a terminal the output stays plain (no colour codes), so it can still be piped."""

from ._shared import (
    EFFECTS, EFFECT_DESC, EFFECT_PALETTE, OFF_NAMES, PALETTES, os, sys,
)
from ._system import term_size
from ._color import COLORS, build_lut, hex_rgb, palette_stops, to256, truecolor_on


class _Style:
    def __init__(self, cfg):
        self.tty = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
        # swatches use 24-bit colour like the installer; 256 colours only when the terminal clearly lacks it
        self.tc = truecolor_on(cfg) or cfg.get("truecolor", "auto").lower() == "auto"
        self.B, self.D, self.Z = ("\x1b[1m", "\x1b[2m", "\x1b[0m") if self.tty else ("", "", "")
        self.M = "\x1b[38;5;183m" if self.tty else ""
        self.G = "\x1b[38;5;114m" if self.tty else ""
        cols = term_size()[0] if self.tty else 0
        self.cols = cols if cols > 0 else 80

    def bg(self, hexv, text="  "):
        if not self.tty:
            return ""
        r, g, b = hex_rgb(hexv) if isinstance(hexv, str) else hexv
        if self.tc:
            return "\x1b[48;2;%d;%d;%dm%s\x1b[0m" % (r, g, b, text)
        return "\x1b[48;5;%dm%s\x1b[0m" % (to256(r, g, b), text)

    def strip(self, stops, width=0):
        """A row of colour blocks: one block per stop, or a smooth gradient `width` cells wide."""
        if not self.tty:
            return ""
        if width:
            return "".join(self.bg(c, " ") for c in build_lut(stops, width))
        return "".join(self.bg(s) for s in stops)


def _cur(cfg, key):
    return (cfg.get(key, "") or "").strip().lower()


def _row(st, i, cur, name, w):
    mark = (st.G + "●" + st.Z) if cur else " "
    return " %s%s%3d)%s %-*s" % (mark, st.M, i, st.Z, w, name)


def cmd_menu_effects(cfg):
    st = _Style(cfg)
    cur = _cur(cfg, "effect")
    off = cur in OFF_NAMES
    names = [e for e in EFFECTS]
    print("\n  %s%d effects%s %s- pick one with: termfx effect NAME   (or its number)%s" % (st.B, len(names), st.Z, st.D, st.Z))
    print("  %scurrent: %s%s\n" % (st.D, "off (still art)" if off else (cur or "aurora"), st.Z))
    wide = st.cols >= 96
    for i, e in enumerate(names, 1):
        pal = EFFECT_PALETTE.get(e, "catppuccin")
        desc = EFFECT_DESC.get(e, "")
        line = _row(st, i, (not off) and e == (cur or "aurora"), e, 14)
        if wide:
            sw = st.strip(palette_stops(pal), 0)
            line += " %s%-36s%s %s %s%s%s" % (st.D, desc, st.Z, sw + " " * max(0, (8 - len(palette_stops(pal))) * 2), st.D, pal, st.Z)
        else:
            room = max(0, st.cols - 28)
            line += " %s%.*s%s" % (st.D, room, desc, st.Z)
        print(line)
    print("   %s  o)%s %-14s %sno effect - still art, nothing animates   (termfx effect off / on)%s" % (st.M, st.Z, "off", st.D, st.Z))
    print("\n  %stry one first:  termfx preview effect=NAME     details:  termfx effect info NAME%s" % (st.D, st.Z))
    return 0


def _hexes(stops):
    return " ".join("#" + s for s in stops)


def cmd_menu_palettes(cfg, key="palette"):
    st = _Style(cfg)
    cur = _cur(cfg, key)
    names = sorted(PALETTES)
    auto_note = "auto = best palette for the effect" if key == "palette" else "auto = match the header palette, rainbow = pastel, off = no colours"
    print("\n  %s%d palettes%s %s- pick one with: termfx %s NAME   (or its number, or \"#hex,#hex,...\")%s" % (
        st.B, len(names), st.Z, st.D, "palette" if key == "palette" else "info-colors", st.Z))
    print("  %scurrent: %s   (%s)%s\n" % (st.D, cur or "auto", auto_note, st.Z))
    wide = st.cols >= 112
    for i, n in enumerate(names, 1):
        stops = PALETTES[n].split()
        head = _row(st, i, n == cur, n, 14) + " %s%d stops%s " % (st.D, len(stops), st.Z)
        sw = st.strip(stops)
        if wide:
            print("%s %s%*s %s%s%s" % (head, sw, (8 - len(stops)) * 2, "", st.D, _hexes(stops), st.Z))
        else:
            print(head + " " + sw)
            if st.tty:
                for chunk in _wrap(_hexes(stops), max(8, st.cols - 10)):
                    print("        %s%s%s" % (st.D, chunk, st.Z))
    auto_on = cur in ("", "auto")
    print("   %s%s  a)%s %-14s %s%s%s" % ((st.G + "●" + st.Z) if auto_on else " ", st.M, st.Z, "auto", st.D, auto_note, st.Z))
    print("\n  %spreview with a gradient:  termfx palette show NAME      single colours:  termfx palette colors%s" % (st.D, st.Z))
    return 0


def _wrap(text, width):
    out, line = [], ""
    for tok in text.split():
        if line and len(line) + 1 + len(tok) > width:
            out.append(line)
            line = tok
        else:
            line = (line + " " + tok).strip()
    if line:
        out.append(line)
    return out


def cmd_menu_colors(cfg):
    st = _Style(cfg)
    cur = _cur(cfg, "palette")
    items = list(COLORS.items())
    print("\n  %s%d colour names%s %s- use one as a solid palette:  termfx palette NAME%s" % (st.B, len(items), st.Z, st.D, st.Z))
    print("  %scurrent palette: %s%s\n" % (st.D, cur or "auto", st.Z))
    percol = 3 if st.cols >= 96 else (2 if st.cols >= 64 else 1)
    cellw = 30
    for start in range(0, len(items), percol):
        parts = []
        for n, h in items[start:start + percol]:
            mark = (st.G + "●" + st.Z) if n == cur else " "
            parts.append(" %s%s %s %-12s %s#%s%s" % (mark, st.bg(h, "    "), "", n, st.D, h, st.Z))
        print("".join(p + " " * max(0, cellw - _vis(p)) for p in parts[:-1]) + parts[-1])
    print("\n  %scombine them:  termfx palette red,white,#00e5ff     any hex:  termfx palette \"#ff8800\"%s" % (st.D, st.Z))
    return 0


def _vis(s):
    import re
    return len(re.sub(r"\x1b\[[0-9;]*m", "", s))


def run(kind, cfg):
    if kind == "effects":
        return cmd_menu_effects(cfg)
    if kind == "palettes":
        return cmd_menu_palettes(cfg)
    if kind == "info-colors":
        return cmd_menu_palettes(cfg, "info_colors")
    if kind == "colors":
        return cmd_menu_colors(cfg)
    return 2
