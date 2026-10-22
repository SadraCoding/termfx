from ._system import (
    as_bool, as_int,
)
from ._art import (
    art_dims, fit_art, is_braille_art, load_art_source, trim_trailing, visible_width,
)
from ._info import (
    get_info,
)

MIN_INFO_W = 28     # narrowest info panel kept for bitmap-like (braille) art, which shrinks gracefully
MIN_INFO_GLYPH = 20  # ...and for text/box-drawing art, which is only kept pixel-perfect at full size
MIN_ART_W = 8       # narrowest art we still draw next to the panel
GOOD_SCALE = 0.6    # side-by-side is kept as long as the art stays at least this big

class Layout:
    pass

def _scale(sw, sh, tw, th):
    return min(1.0, tw / max(1, sw), th / max(1, sh))

def build_layout(cfg, cols, rows, force=False):
    """Decide where the art and the info panel go so that they can never overlap.

    Three arrangements are tried:
      side     art on the left, info panel on the right (the default look)
      stacked  art on top, info panel underneath (for wide art that would be crushed beside the panel)
      art      art only (when there is no room for the panel at all)
    The art is always scaled as a whole to fit; it is never cropped (unless `fit = crop` is set)."""
    if not force:
        if not as_bool(cfg["enabled"]):
            return None
        if cols < as_int(cfg["min_cols"], 90) or rows < as_int(cfg["min_rows"], 30):
            return None
    cap = max(6, rows - as_int(cfg["reserve"], 12))          # tallest header the terminal can spare
    gap = max(1, as_int(cfg["info_gap"], 4))
    th_max = max(4, min(as_int(cfg["max_height"], 24), cap))
    total = max(12, cols - 1)                                # keep the last column free
    src, path = load_art_source(cfg)
    sw, sh = art_dims(src)
    uw = as_int(cfg["max_width"], 0)
    wcap = uw if uw > 0 else max(cols // 2, min(sw, (cols * 3) // 4))
    wcap = max(6, min(wcap, total - 2))                      # the art box is art + 2 spare columns

    info = [trim_trailing(l) for l in get_info(cfg)]
    iw = max((visible_width(l) for l in info), default=0)
    ih = len(info)
    if not iw:
        info, ih = [], 0

    glyph = not is_braille_art(src)      # letters / line art / box drawing: any shrinking costs detail
    min_info = MIN_INFO_GLYPH if glyph else MIN_INFO_W
    best = ("art", wcap, th_max, _scale(sw, sh, wcap, th_max))
    if info:
        want = min(wcap, sw)
        room = total - gap - 2 - want
        i_eff = iw if room >= iw else max(min(iw, min_info), room)
        tw_side = min(wcap, total - gap - 2 - min(i_eff, iw))
        side = ("side", tw_side, th_max, _scale(sw, sh, tw_side, th_max)) if tw_side >= MIN_ART_W else None
        th_st = min(th_max, cap - ih - 1)
        stacked = ("stacked", wcap, th_st, _scale(sw, sh, wcap, th_st)) if th_st >= 4 else None
        chosen = None
        if glyph:                         # text art: take the first arrangement that shows it at 100%
            chosen = next((c for c in (side, stacked) if c and c[3] >= 0.98), None)
        if chosen is None:
            chosen = side
            if stacked and (chosen is None or (chosen[3] < GOOD_SCALE and stacked[3] >= chosen[3] + 0.25)):
                chosen = stacked
            if chosen is None or chosen[3] < 0.4:
                if chosen is None or best[3] >= chosen[3] + 0.25:
                    chosen = best
            elif glyph and chosen[3] < 0.75 and best[3] >= 0.98:
                chosen = best             # a crushed text logo is worse than no panel
        best = chosen

    mode, tw, th, _ = best
    frames = fit_art(cfg, src, path, tw, th)
    aw, ah = art_dims(frames)
    L = Layout()
    L.frames, L.path, L.aw, L.ah, L.mode = frames, path, aw, ah, mode
    L.src_w, L.src_h = sw, sh
    L.scale = min(1.0, aw / max(1, sw), ah / max(1, sh)) if (aw < sw or ah < sh) else 1.0
    L.cols, L.rows = cols, rows
    L.info, L.info_w = [], 0
    L.info_y = 0

    if mode == "side":
        iwid = min(iw, total - gap - aw - 2)
        if iwid < 10:
            mode = L.mode = "art"
        else:
            L.info, L.info_w = info, iwid
            L.H = max(ah, min(ih, cap))
            L.art_y, L.art_rows = (L.H - ah) // 2, L.H
            L.info_y = max(0, (L.H - min(ih, L.H)) // 2)
            vis_w = extent = aw + 2 + gap + iwid
    elif mode == "stacked":
        L.info, L.info_w = info, min(iw, total)
        L.H = ah + 1 + ih
        L.art_y, L.art_rows, L.info_y = 0, ah, ah + 1
        vis_w, extent = max(aw, L.info_w), max(aw + 2, L.info_w)
    if mode == "art":
        L.H = ah
        L.art_y, L.art_rows = 0, ah
        vis_w, extent = aw, aw + 2

    align = (cfg.get("align") or "left").strip().lower()
    if align == "center":
        pad = (cols - vis_w) // 2
    elif align == "right":
        pad = cols - 1 - vis_w
    else:
        pad = 0
    pad = max(0, min(pad, cols - extent))                    # the whole block always stays on screen
    L.pad = L.art_x = pad
    L.info_x = pad + aw + 2 + gap if L.mode == "side" else pad
    L.info_col = L.info_x
    return L
