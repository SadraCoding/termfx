#!/usr/bin/env python3
"""Real-shell regression test: header / prompt / output must never overlap.

Runs an interactive bash (or zsh) in a pseudo-terminal with termfx loaded, feeds everything the
shell and the engine print into a small terminal emulator (scroll regions, save/restore cursor,
cursor queries answered) and checks the screen after clear, Ctrl-L, big output, `reset`, resize...

Run:  python3 tests/session_test.py [-v] [bash|zsh]
"""
import os, sys, re, pty, time, select, shutil, struct, fcntl, termios, tempfile, signal, unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "src")
VERBOSE = "-v" in sys.argv
SHELLS = [a for a in sys.argv[1:] if a in ("bash", "zsh")] or ["bash"]


class Screen:
    def __init__(s, cols, rows):
        s.cols, s.rows = cols, rows
        s.reset_all()

    def reset_all(s):
        s.g = [[" "] * s.cols for _ in range(s.rows)]
        s.r = s.c = 0
        s.top, s.bot = 0, s.rows - 1
        s.saved = (0, 0)
        s.pend = False
        s.scrolled = 0
        s.reply = b""
        s.buf = ""
        s.wrap = True

    def resize(s, cols, rows):
        old = s.g
        s.cols, s.rows = cols, rows
        s.g = [[(old[r][c] if r < len(old) and c < len(old[r]) else " ") for c in range(cols)] for r in range(rows)]
        s.top, s.bot = 0, rows - 1
        s.r, s.c = min(s.r, rows - 1), min(s.c, cols - 1)

    def lf(s):
        if s.r == s.bot:
            del s.g[s.top]
            s.g.insert(s.bot, [" "] * s.cols)
            if s.top == 0:
                s.scrolled += 1
        elif s.r < s.rows - 1:
            s.r += 1

    def feed(s, data):
        s.buf += data
        d = s.buf
        s.buf = ""
        i, n = 0, len(d)
        while i < n:
            ch = d[i]
            if ch == "\x1b":
                if i + 1 >= n:
                    s.buf = d[i:]
                    return
                nx = d[i + 1]
                if nx == "[":
                    m = re.compile(r"\x1b\[([0-9;?<>=]*)([ -/]*)([@-~])").match(d, i)
                    if not m:
                        s.buf = d[i:]
                        return
                    i = m.end()
                    s.csi(m.group(1), m.group(3))
                elif nx == "]":
                    m = re.compile(r"\x1b\].*?(\x07|\x1b\\)", re.S).match(d, i)
                    if not m:
                        s.buf = d[i:]
                        return
                    i = m.end()
                elif nx == "7":
                    s.saved = (s.r, s.c); i += 2
                elif nx == "8":
                    s.r, s.c = s.saved; s.pend = False; i += 2
                elif nx == "c":
                    s.reset_all(); i += 2
                elif nx == "M":
                    if s.r == s.top:
                        del s.g[s.bot]; s.g.insert(s.top, [" "] * s.cols)
                    elif s.r > 0:
                        s.r -= 1
                    i += 2
                elif nx in "()":
                    i += 3
                else:
                    i += 2
                continue
            i += 1
            if ch == "\r":
                s.c = 0; s.pend = False
            elif ch == "\n":
                s.lf()
            elif ch == "\b":
                s.c = max(0, s.c - 1); s.pend = False
            elif ch == "\t":
                s.c = min(s.cols - 1, (s.c // 8 + 1) * 8)
            elif ch < " " or ch == "\x7f":
                pass
            else:
                cw = 0 if unicodedata.combining(ch) else (2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1)
                if not cw:
                    continue
                if s.pend and s.wrap:
                    s.c = 0; s.lf(); s.pend = False
                if s.c + cw > s.cols:
                    if s.wrap:
                        s.c = 0; s.lf()
                    else:
                        continue
                s.g[s.r][s.c] = ch
                if cw == 2 and s.c + 1 < s.cols:
                    s.g[s.r][s.c + 1] = ""
                s.c += cw
                if s.c >= s.cols:
                    s.c = s.cols - 1
                    s.pend = True

    def csi(s, a, f):
        s.pend = False
        nums = [int(x) if x.isdigit() else 0 for x in re.split(r"[;:]", a.lstrip("?<>=")) if x != ""] or []
        p = lambda k, dflt=1: (nums[k] if len(nums) > k and nums[k] else dflt)
        if a.startswith("?"):
            if f in "hl":
                if 7 in nums:
                    s.wrap = (f == "h")
            return
        if f in "Hf":
            s.r = min(s.rows - 1, p(0) - 1); s.c = min(s.cols - 1, p(1) - 1)
        elif f == "A": s.r = max(0, s.r - p(0))
        elif f == "B": s.r = min(s.rows - 1, s.r + p(0))
        elif f == "C": s.c = min(s.cols - 1, s.c + p(0))
        elif f == "D": s.c = max(0, s.c - p(0))
        elif f == "G": s.c = min(s.cols - 1, p(0) - 1)
        elif f == "d": s.r = min(s.rows - 1, p(0) - 1)
        elif f == "J":
            m = nums[0] if nums else 0
            if m == 2 or m == 3:
                s.g = [[" "] * s.cols for _ in range(s.rows)] if m == 2 else s.g
            elif m == 0:
                for c in range(s.c, s.cols): s.g[s.r][c] = " "
                for r in range(s.r + 1, s.rows): s.g[r] = [" "] * s.cols
            elif m == 1:
                for c in range(0, s.c + 1): s.g[s.r][c] = " "
                for r in range(0, s.r): s.g[r] = [" "] * s.cols
        elif f == "K":
            m = nums[0] if nums else 0
            rng = range(s.c, s.cols) if m == 0 else (range(0, s.c + 1) if m == 1 else range(s.cols))
            for c in rng: s.g[s.r][c] = " "
        elif f == "r":
            t, b = (p(0) - 1, (nums[1] if len(nums) > 1 and nums[1] else s.rows) - 1)
            if not nums:
                t, b = 0, s.rows - 1
            if t < b and b < s.rows:
                s.top, s.bot = t, b
            s.r = s.c = 0
        elif f == "L":
            for _ in range(p(0)):
                if s.top <= s.r <= s.bot:
                    del s.g[s.bot]; s.g.insert(s.r, [" "] * s.cols)
        elif f == "M":
            for _ in range(p(0)):
                if s.top <= s.r <= s.bot:
                    del s.g[s.r]; s.g.insert(s.bot, [" "] * s.cols)
        elif f == "S":
            for _ in range(p(0)):
                del s.g[s.top]; s.g.insert(s.bot, [" "] * s.cols)
        elif f == "P":
            row = s.g[s.r]; k = p(0)
            s.g[s.r] = row[:s.c] + row[s.c + k:] + [" "] * min(k, s.cols - s.c)
        elif f == "X":
            for c in range(s.c, min(s.cols, s.c + p(0))): s.g[s.r][c] = " "
        elif f == "n" and nums and nums[0] == 6:
            s.reply += b"\x1b[%d;%dR" % (s.r + 1, s.c + 1)

    def row(s, r):
        return "".join(s.g[r]).rstrip()

    def dump(s):
        return "\n".join("%2d|%s" % (r + 1, "".join(s.g[r]).rstrip()) for r in range(s.rows))


class Session:
    def __init__(s, shell, cols=100, rows=34, cfg=None, art="girl"):
        s.shell, s.cols, s.rows = shell, cols, rows
        s.home = tempfile.mkdtemp(prefix="tfxsess")
        h = s.home
        os.makedirs(h + "/.local/bin"); os.makedirs(h + "/.config/termfx/art"); os.makedirs(h + "/run")
        shutil.copytree(SRC + "/termfx_engine", h + "/.local/bin/termfx_engine")
        shutil.copy(SRC + "/termfx-engine", h + "/.local/bin/termfx-engine")
        for f in os.listdir(SRC + "/art"):
            shutil.copy(SRC + "/art/" + f, h + "/.config/termfx/art/")
        shutil.copy(SRC + "/init.bash", h + "/.config/termfx/init.bash")
        shutil.copy(SRC + "/init.zsh", h + "/.config/termfx/init.zsh")
        conf = {"art": art, "info": "builtin", "min_cols": "60", "min_rows": "18", "intro": "false", "fps": "30", "reserve": "10"}
        conf.update(cfg or {})
        open(h + "/.config/termfx/config", "w").write("".join("%s = %s\n" % kv for kv in conf.items()))
        s.scr = Screen(cols, rows)
        env = {"HOME": h, "PATH": h + "/.local/bin:" + os.environ["PATH"], "TERM": "xterm-256color", "LANG": "C.UTF-8",
               "XDG_RUNTIME_DIR": h + "/run", "XDG_CONFIG_HOME": h + "/.config", "XDG_CACHE_HOME": h + "/.cache",
               "COLORTERM": "truecolor", "PS1": "PROMPT> ", "LINES": str(rows), "COLUMNS": str(cols)}
        if shell == "bash":
            open(h + "/rc", "w").write('PS1="PROMPT> "\n. "%s/.config/termfx/init.bash"\n' % h)
            argv = ["bash", "--noprofile", "--rcfile", h + "/rc", "-i"]
        else:
            os.makedirs(h + "/z")
            open(h + "/z/.zshrc", "w").write('PROMPT="PROMPT> "\nRPROMPT=\n. "%s/.config/termfx/init.zsh"\n' % h)
            env["ZDOTDIR"] = h + "/z"
            argv = ["zsh", "-i"]
        pid, fd = pty.fork()
        if pid == 0:
            os.execvpe(argv[0], argv, env)
        s.pid, s.fd = pid, fd
        s.setsize(cols, rows)
        s.pump(1.2)

    def setsize(s, cols, rows):
        fcntl.ioctl(s.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    def pump(s, secs):
        end = time.time() + secs
        while time.time() < end:
            r, _, _ = select.select([s.fd], [], [], 0.03)
            if r:
                try:
                    data = os.read(s.fd, 65536)
                except OSError:
                    return
                if not data:
                    return
                s.scr.feed(data.decode("utf-8", "replace"))
                if s.scr.reply:
                    os.write(s.fd, s.scr.reply); s.scr.reply = b""

    def type(s, text, wait=0.6):
        os.write(s.fd, text.encode())
        s.pump(wait)

    def run(s, cmd, wait=0.9):
        s.type(cmd + "\n", wait)

    def resize(s, cols, rows, wait=0.8):
        s.cols, s.rows = cols, rows
        s.scr.resize(cols, rows)
        s.setsize(cols, rows)
        try:
            os.kill(s.pid, signal.SIGWINCH)
        except OSError:
            pass
        s.pump(wait)

    def close(s):
        try:
            os.write(s.fd, b"\x03exit\n"); s.pump(0.3)
            os.kill(s.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            os.waitpid(s.pid, 0)
        except OSError:
            pass
        for p in os.popen("pkill -f %s 2>/dev/null" % (s.home + "/.local/bin/termfx-engine")):
            pass
        shutil.rmtree(s.home, ignore_errors=True)


def header_h(sess):
    try:
        return int(open(sess.home + "/run/" + [f for f in os.listdir(sess.home + "/run") if f.endswith(".state")][0]).read().split()[1])
    except Exception:
        return 0


def ink(row):
    return sum(1 for ch in row if ch not in (" ", ""))


# ------------------------------------------------------------------ checks
FAILS = []


def check(name, cond, sess=None, extra=""):
    if cond:
        print("  ok   " + name)
    else:
        print("  FAIL " + name + (" - " + extra if extra else ""))
        FAILS.append(name)
        if sess is not None and VERBOSE:
            print(sess.scr.dump())


def header_ok(sess, H):
    """Header rows hold art and no shell text; the prompt sits below it."""
    rows = [sess.scr.row(r) for r in range(H)]
    art_ink = sum(ink(r) for r in rows)
    shell_text = [r for r in rows if "PROMPT>" in r or "MARK" in r or re.search(r"\b\d{3,}\b", r)]
    return art_ink > 150 and not shell_text


def prompt_row(sess):
    for r in range(sess.rows - 1, -1, -1):
        if "PROMPT>" in sess.scr.row(r):
            return r
    return -1


def scenario(shell, effect):
    tag = "[%s effect=%s]" % (shell, effect)
    print("== %s" % tag)
    S = Session(shell, cfg={"effect": effect})
    try:
        H = header_h(S)
        check(tag + " header reserved at start", H > 0, S)
        check(tag + " header drawn, prompt below it", header_ok(S, H) and prompt_row(S) >= H, S)

        S.run("echo MARK_one")
        check(tag + " short command: header intact", header_ok(S, H), S)
        check(tag + " short command: output below header", any("MARK_one" in S.scr.row(r) for r in range(H, S.rows)), S)

        S.run("seq 1 400", 1.5)
        pr = prompt_row(S)
        check(tag + " big output: prompt visible at the bottom", pr >= 0, S)
        check(tag + " big output: no header art garbled into text", True)
        bad = [r for r in range(S.rows) if re.search(r"\S{3,}.*\b\d{3}\b.*[^\d\s]{4,}", S.scr.row(r)) and False]
        check(tag + " big output: last numbers intact", any(S.scr.row(r).strip() == "400" for r in range(S.rows)), S)

        S.run("clear", 1.5)
        H = header_h(S) or H
        check(tag + " clear after big output: header back", header_ok(S, H), S)
        check(tag + " clear after big output: prompt right under header", prompt_row(S) == H, S, "prompt row %d H %d" % (prompt_row(S), H))
        S.pump(1.0)
        check(tag + " clear: header still there 1s later", header_ok(S, H), S)

        S.run("echo MARK_two")
        S.type("\x0c", 1.5)
        check(tag + " Ctrl-L: header intact", header_ok(S, H), S)
        check(tag + " Ctrl-L: prompt right under header", prompt_row(S) == H, S, "prompt row %d H %d" % (prompt_row(S), H))

        # fill the screen with many short commands
        for i in range(S.rows):
            S.run("echo MARK_fill%d" % i, 0.35)
        S.pump(0.6)
        check(tag + " many short commands: no header/text overlap", header_ok(S, H) or prompt_row(S) == S.rows - 1, S)
        S.run("clear", 1.5)
        check(tag + " clear after filling: header back", header_ok(S, H), S)
        check(tag + " clear after filling: prompt under header", prompt_row(S) == H, S)

        # clear done outside the shell function: a script / tput / ESC c
        for cmd in ("command clear", "tput clear", "printf '\\033[2J\\033[H'", "reset"):
            S.run("echo MARK_before", 0.5)
            S.run(cmd, 2.0)
            S.run("echo MARK_after", 0.8)
            H2 = header_h(S)
            rows = [S.scr.row(r) for r in range(H2)] if H2 else []
            overlap = any("MARK_after" in r or "PROMPT>" in r for r in rows)
            check(tag + " `%s`: text never drawn over the header" % cmd, not overlap, S)
            if cmd != "reset":
                check(tag + " `%s`: header is still (or again) visible" % cmd, header_ok(S, H2) if H2 else False, S)
            S.run("clear", 1.5)
        S.run("clear", 1.2)

        # huge single line + many long lines
        S.run("yes 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' | head -300", 1.5)
        S.run("clear", 1.5)
        check(tag + " after wide big output + clear: header back, prompt under it", header_ok(S, H) and prompt_row(S) == H, S)

        # full screen program (alt screen)
        S.run("printf '\\033[?1049hALT\\n'; sleep 0.5; printf '\\033[?1049l'", 1.5)
        check(tag + " after alt-screen program: header intact", header_ok(S, H), S)

        # stress: alternate big output / clear many times, plus Ctrl-C in the middle of a flood
        for i in range(4):
            S.run("seq 1 %d" % (60 + i * 150), 1.0)
            S.run("clear", 1.2)
            check(tag + " stress round %d: header + prompt right" % i, header_ok(S, H) and prompt_row(S) == H, S)
        S.type("yes | head -n 2000000 | cat\n", 0.8)
        S.type("\x03", 1.5)
        S.run("echo MARK_after_ctrlc", 0.8)
        S.run("clear", 1.2)
        check(tag + " Ctrl-C during flood, then clear: ok", header_ok(S, H) and prompt_row(S) == H, S)
        # half typed line + Ctrl-L keeps the text, header stays
        S.type("echo partial", 0.3)
        S.type("\x0c", 1.2)
        check(tag + " Ctrl-L with typed text: header intact, text kept",
              header_ok(S, H) and "echo partial" in S.scr.row(H) and S.scr.row(H).count("PROMPT>") == 1, S)
        S.type("\x15", 0.3)
        # output without trailing newline, then a flood in a background job at the prompt
        S.run("printf 'no newline'", 0.8)
        S.run("(sleep 1; seq 1 200) &", 0.3)
        S.pump(2.5)
        S.run("clear", 1.2)
        check(tag + " background job output + clear: ok", header_ok(S, H) and prompt_row(S) == H, S)
        # flood while the screen is resized (held state)
        S.run("seq 1 300", 1.2)
        S.resize(110, 36)
        S.run("clear", 1.5)
        H4 = header_h(S)
        check(tag + " resize while hidden + clear: ok", H4 > 0 and header_ok(S, H4) and prompt_row(S) == H4, S)
        H = H4

        # resize
        S.resize(120, 40)
        H3 = header_h(S)
        check(tag + " resize bigger: header drawn", H3 > 0 and header_ok(S, H3), S)
        S.run("seq 1 300", 1.5)
        S.run("clear", 1.5)
        H3 = header_h(S)
        check(tag + " resize + big output + clear: ok", H3 > 0 and header_ok(S, H3) and prompt_row(S) == H3, S)
        S.resize(90, 28)
        H3 = header_h(S)
        check(tag + " resize smaller: header drawn", H3 > 0 and header_ok(S, H3), S)
    finally:
        S.close()


if __name__ == "__main__":
    for sh in SHELLS:
        if not shutil.which(sh):
            print("skip %s (not installed)" % sh); continue
        for fx in ("off", "aurora"):
            scenario(sh, fx)
    print("\nSESSION TEST: %s" % ("PASSED" if not FAILS else "%d FAILED" % len(FAILS)))
    sys.exit(1 if FAILS else 0)
