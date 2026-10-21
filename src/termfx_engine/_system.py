from ._shared import (
    CACHE_DIR, CONF_FILE, DEFAULTS, OVERRIDES, os,
    re, select, shutil, time, traceback,
)

_TTY_FD = None

def log_error():
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(os.path.join(CACHE_DIR, "error.log"), "a") as fh:
            fh.write(time.strftime("%F %T ") + traceback.format_exc() + "\n")
    except Exception:
        pass

def as_bool(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y")

def as_int(v, d):
    try:
        return int(float(str(v).strip()))
    except Exception:
        return d

def as_float(v, d):
    try:
        return float(str(v).strip())
    except Exception:
        return d

def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONF_FILE, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line[0] in "#;" or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip()
                if v[:1] in ("\"", "'") and v.count(v[0]) >= 2:    # quoted: keep everything inside the quotes
                    v = v[1:v.index(v[0], 1)]
                else:                                              # unquoted: strip a trailing " # comment"
                    v = re.sub(r"\s+#.*$", "", v).strip()
                cfg[k.strip().lower()] = v
    except OSError:
        pass
    for k in list(cfg):
        ev = os.environ.get("TERMFX_" + k.upper())
        if ev is not None:
            cfg[k] = ev
    cfg.update(OVERRIDES)
    return cfg

def _tty_fd():
    global _TTY_FD
    if _TTY_FD is None:
        try:
            _TTY_FD = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
        except OSError:
            _TTY_FD = -1
    return _TTY_FD

def term_size():
    fd = _tty_fd()
    cands = ([fd] if fd >= 0 else []) + [1, 2, 0]
    for f in cands:
        try:
            s = os.get_terminal_size(f)
            if s.columns > 0 and s.lines > 0:
                return s.columns, s.lines
        except OSError:
            pass
    s = shutil.get_terminal_size((0, 0))
    return s.columns, s.lines

class Out:
    def __init__(self):
        fd = _tty_fd()
        self.fd = fd if fd >= 0 else 1

    def write(self, s):
        data = s.encode("utf-8", "replace")
        while data:
            try:
                n = os.write(self.fd, data)
            except InterruptedError:
                continue
            except BlockingIOError:
                select.select([], [self.fd], [], 0.2)
                continue
            data = data[n:]

def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
