#!/usr/bin/env python3
"""Overlap hunt: realistic ways a header can end up under / over command output.

Reuses the pseudo-terminal harness of session_test.py.  Run:  python3 tests/overlap_test.py [-v] [bash|zsh]
Every case must end with the header rows holding EITHER the clean animated header OR no header art at all
(never a mix of art and shell text), and with the command's output intact.
"""
import sys, os, re, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session_test as T
from session_test import Session, check, ink, header_h, prompt_row, header_ok


def art_ink(S, H):
    return sum(1 for r in range(H) for ch in S.scr.row(r) if "\u2800" <= ch <= "\u28ff")


def clean(S, H):
    """header rows: clean header, or nothing of it (hidden); never art mixed with shell text."""
    if H <= 0:
        return False
    if header_ok(S, H):
        return True
    return art_ink(S, H) == 0


def numbers_intact(S, last):
    seen = [S.scr.row(r).strip() for r in range(S.rows)]
    return str(last) in seen


def case(shell, effect):
    tag = "[%s %s]" % (shell, effect)
    print("== " + tag)
    S = Session(shell, cfg={"effect": effect, "fps": "60"})
    try:
        H = header_h(S)
        check(tag + " header reserved", H > 0, S)

        # 1. typing while the header animates
        text = "echo typed_while_animating_0123456789"
        for ch in text:
            S.type(ch, 0.03)
        S.pump(0.4)
        pr = prompt_row(S)
        check(tag + " typing under animation: text intact on the prompt row", pr >= 0 and text in S.scr.row(pr), S, S.scr.row(pr))
        check(tag + " typing under animation: header clean", header_ok(S, H), S)
        S.type("\n", 0.9)
        check(tag + " typed command ran, output below header", any("typed_while_animating_0123456789" == S.scr.row(r).strip() for r in range(H, S.rows)), S)

        # 2. command line longer than the screen width (wraps over several rows)
        long = "echo " + "w" * 230
        S.run(long, 1.2)
        check(tag + " wrapped command line: header clean", clean(S, H), S)

        # 3. output that ends without a newline
        S.run("printf 'no_newline_here'", 1.0)
        check(tag + " no trailing newline: header clean", clean(S, H), S)
        check(tag + " no trailing newline: output kept", any("no_newline_here" in S.scr.row(r) for r in range(S.rows)), S)

        # 4. big output, then cursor moved up (progress-bar style) so the cursor ends mid-screen
        S.run("seq 1 120; printf '\\e[18A'", 1.6)
        check(tag + " scrolled output + cursor-up: header clean (no art over numbers)", clean(S, H), S)
        S.run("", 0.8)
        check(tag + " scrolled output + cursor-up, next prompt: clean", clean(S, H), S)
        S.run("clear", 1.0)
        check(tag + " clear brings the header back", header_ok(S, H) and prompt_row(S) == H, S)

        # 5. two-line prompt close to the bottom, output just below the screen height
        S.run("PS1=$'first_line\\nPROMPT> '", 0.8)
        for n in (S.rows - H - 4, S.rows - H - 2, S.rows - H - 1, S.rows - H, S.rows - H + 1, S.rows):
            S.run("clear", 0.9)
            S.run("seq 1 %d" % n, 1.4)
            check(tag + " two-line prompt, %d lines of output: header clean" % n, clean(S, H), S)
            check(tag + " two-line prompt, %d lines of output: last number intact" % n, numbers_intact(S, n), S)
        S.run("PS1='PROMPT> '", 0.8)
        S.run("clear", 0.9)

        # 6. terminal that never answers the cursor-position query (slow ssh, tmux, odd terminals)
        S.scr_answer = S.scr.reply
        orig = S.scr.csi
        def deaf(a, f, orig=orig):
            if f == "n":
                return
            orig(a, f)
        S.scr.csi = deaf
        S.run("seq 1 120", 2.2)
        check(tag + " no cursor report: header clean after big output", clean(S, H), S)
        check(tag + " no cursor report: no stray escape text at the prompt", "[" not in S.scr.row(max(prompt_row(S), 0)).replace("PROMPT>", ""), S)
        S.run("echo after_deaf", 1.2)
        check(tag + " no cursor report: next command fine", clean(S, H) and any(S.scr.row(r) == "after_deaf" for r in range(S.rows)), S)
        S.scr.csi = orig
        S.run("clear", 1.0)
        check(tag + " clear recovers header", header_ok(S, H) and prompt_row(S) == H, S)

        # 7. many commands in a row, each printing a few lines (fills the screen gradually)
        for i in range(14):
            S.run("echo MARK_%d; echo b; echo c; echo d" % i, 0.7)
            ok = clean(S, H)
            if not ok:
                break
        check(tag + " gradual filling: header clean at every step (stopped at %d)" % i, ok, S)
    finally:
        S.close()


if __name__ == "__main__":
    for sh in T.SHELLS:
        if not T.shutil.which(sh):
            print("skip " + sh); continue
        for fx in ("aurora", "off"):
            case(sh, fx)
    print("\nOVERLAP TEST: %s" % ("PASSED" if not T.FAILS else "%d FAILED" % len(T.FAILS)))
    sys.exit(1 if T.FAILS else 0)
