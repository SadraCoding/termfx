from ._system import (
    as_bool, as_int,
)
from ._art import (
    load_art_frames,
)
from ._info import (
    get_info,
)

class Layout:
    pass

def build_layout(cfg, cols, rows, force=False):
    if not force:
        if not as_bool(cfg["enabled"]):
            return None
        if cols < as_int(cfg["min_cols"], 90) or rows < as_int(cfg["min_rows"], 30):
            return None
    cap = max(6, rows - as_int(cfg["reserve"], 12))
    gap = max(1, as_int(cfg["info_gap"], 4))
    info = get_info(cfg)
    th = max(4, min(as_int(cfg["max_height"], 24), cap))
    tw = as_int(cfg["max_width"], 0) or max(20, int(cols * 0.5))
    if info:
        tw = min(tw, max(20, cols - gap - 42))
    frames, path = load_art_frames(cfg, tw, th)
    ah = max(len(f) for f in frames)
    aw = max(len(r) for f in frames for r in f)
    L = Layout()
    L.frames, L.path, L.aw, L.ah = frames, path, aw, ah
    L.info_col = aw + 2 + gap
    if info and cols - L.info_col + 1 < 28:
        info = []
    L.info = info
    L.H = min(max(ah, len(info)), cap)
    if L.H < ah:
        L.H = ah
    L.cols, L.rows = cols, rows
    return L
