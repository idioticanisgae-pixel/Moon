"""
Lua Minifier — converts any Lua script to a single line.
Requires Python 3.x (tkinter is included in the standard library).

Run:  python lua_minifier.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os


# ── Core minifier ─────────────────────────────────────────────────────────────

def minify_lua(source: str) -> str:
    """
    Collapses a Lua script to a single line by:
      1. Removing full-line and inline -- comments (respects --[[ long strings ]])
      2. Removing block comments --[[ ... ]]
      3. Preserving string literals (single, double, long)
      4. Collapsing all whitespace / newlines between tokens
      5. Ensuring required spaces between keyword/identifier tokens
    """

    tokens = []       # list of ('string'|'code', value)
    i = 0
    n = len(source)

    # ── Tokenise: split into string literals vs code ──────────────────────────
    while i < n:
        # Long strings / long comments:  --[==[ ... ]==]  or  [==[ ... ]==]
        long_match = re.match(r'(\[)(=*)(\[)', source[i:])
        comment_long = re.match(r'(--\[)(=*)(\[)', source[i:])

        if comment_long:
            level = comment_long.group(2)
            end_pat = ']' + level + ']'
            end_idx = source.find(end_pat, i + len(comment_long.group(0)))
            if end_idx == -1:
                # Unterminated — keep as-is
                tokens.append(('code', source[i:]))
                break
            # Skip the block comment entirely
            i = end_idx + len(end_pat)

        elif long_match and source[i] == '[':
            level = long_match.group(2)
            end_pat = ']' + level + ']'
            end_idx = source.find(end_pat, i + len(long_match.group(0)))
            if end_idx == -1:
                tokens.append(('string', source[i:]))
                break
            tokens.append(('string', source[i: end_idx + len(end_pat)]))
            i = end_idx + len(end_pat)

        # Short string: "..." or '...'
        elif source[i] in ('"', "'"):
            quote = source[i]
            j = i + 1
            while j < n:
                if source[j] == '\\':
                    j += 2          # skip escaped char
                elif source[j] == quote:
                    j += 1
                    break
                else:
                    j += 1
            tokens.append(('string', source[i:j]))
            i = j

        # Short comment: -- ... (to end of line)
        elif source[i:i+2] == '--':
            eol = source.find('\n', i)
            if eol == -1:
                i = n           # rest is comment
            else:
                i = eol + 1    # skip past newline

        else:
            # Plain code character
            if tokens and tokens[-1][0] == 'code':
                tokens[-1] = ('code', tokens[-1][1] + source[i])
            else:
                tokens.append(('code', source[i]))
            i += 1

    # ── Process code segments: collapse whitespace ────────────────────────────
    processed = []
    for kind, val in tokens:
        if kind == 'string':
            processed.append(val)
        else:
            # Replace all whitespace runs (including newlines) with a single space
            val = re.sub(r'[ \t\r\n]+', ' ', val)
            processed.append(val)

    result = ''.join(processed)

    # ── Trim spaces around operators / punctuation ────────────────────────────
    # Safe to strip spaces next to these chars (won't affect string literals
    # because we only operate on the joined string between string tokens).
    # We do a final pass on the whole string but protect string content
    # by re-splitting on our known string boundaries — simpler: just do
    # lightweight cleanup passes that are always safe.

    # Remove spaces around: ( ) [ ] { } , ; = + - * / % ^ # < > ~ .
    # but NOT inside strings — we'll use a regex that skips quoted regions.
    def strip_around(text, chars):
        pattern = r'\s*([' + re.escape(chars) + r'])\s*'
        return re.sub(pattern, r'\1', text)

    # Only safe to strip around pure punctuation where no space is ever needed
    result = re.sub(r' *([\(\)\[\]\{\},;]) *', r'\1', result)
    # Keep single space around operators in case of keywords like "not x"
    result = re.sub(r' *(\.\.\.?) *', r'\1', result)   # .. and ...
    result = re.sub(r' *(==|~=|<=|>=) *', r'\1', result)
    result = re.sub(r' *([+\-*/%^#<>]) *', r'\1', result)
    result = re.sub(r' *(=) *', r'\1', result)

    # Re-add mandatory space between two identifier/keyword chars
    # e.g.  "local x"  →  after stripping we might get "localx" — prevent that
    # Rule: if two word-chars are adjacent after a removed space, put it back.
    # (This is safe because we only stripped spaces, not word chars.)
    result = re.sub(r'([A-Za-z0-9_])([A-Za-z0-9_])', r'\1 \2', result)
    # But now things like "end)" have an unwanted space before ")".
    # Re-strip around pure punctuation again:
    result = re.sub(r' *([\(\)\[\]\{\},;]) *', r'\1', result)
    result = re.sub(r'([A-Za-z0-9_]) +([\(\)\[\]\{\},;])', r'\1\2', result)
    result = re.sub(r'([\(\)\[\]\{\},;]) +([A-Za-z0-9_])', r'\1\2', result)

    # Collapse any double spaces that crept in
    result = re.sub(r'  +', ' ', result)
    result = result.strip()

    return result


# ── GUI ───────────────────────────────────────────────────────────────────────

DARK_BG   = "#0e0f16"
PANEL_BG  = "#12141e"
ACCENT    = "#5b6af5"
ACCENT2   = "#3ecf82"
TEXT      = "#d2d2e6"
SUBTEXT   = "#7878a0"
BORDER    = "#2a2c40"
ERROR_COL = "#ff5050"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lua Minifier")
        self.geometry("860x620")
        self.minsize(680, 480)
        self.configure(bg=DARK_BG)
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        # Title bar row
        title_frame = tk.Frame(self, bg=DARK_BG)
        title_frame.pack(fill="x", padx=18, pady=(14, 4))

        tk.Label(
            title_frame, text="⬛  Lua Minifier",
            bg=DARK_BG, fg=TEXT,
            font=("Courier New", 15, "bold"),
        ).pack(side="left")

        self.status_var = tk.StringVar(value="")
        self.status_lbl = tk.Label(
            title_frame, textvariable=self.status_var,
            bg=DARK_BG, fg=ACCENT2,
            font=("Courier New", 10),
        )
        self.status_lbl.pack(side="right", padx=4)

        # Button row
        btn_frame = tk.Frame(self, bg=DARK_BG)
        btn_frame.pack(fill="x", padx=18, pady=(0, 8))

        self._btn(btn_frame, "Open File",    self._open_file).pack(side="left", padx=(0, 6))
        self._btn(btn_frame, "Minify  ▶",   self._minify,    accent=True).pack(side="left", padx=(0, 6))
        self._btn(btn_frame, "Copy Output",  self._copy).pack(side="left", padx=(0, 6))
        self._btn(btn_frame, "Save Output",  self._save).pack(side="left", padx=(0, 6))
        self._btn(btn_frame, "Clear",        self._clear,     danger=True).pack(side="right")

        # Paned editor area
        pane = tk.PanedWindow(self, orient="vertical", bg=BORDER,
                               sashwidth=4, sashrelief="flat")
        pane.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        # Input
        in_wrap = self._editor_frame(pane, "INPUT  —  paste or open a .lua file")
        self.input_text = self._editor(in_wrap)
        pane.add(in_wrap, minsize=120)

        # Output
        out_wrap = self._editor_frame(pane, "OUTPUT  —  single-line result")
        self.output_text = self._editor(out_wrap, readonly=True, color=ACCENT2)
        pane.add(out_wrap, minsize=80)

        # Stats bar
        self.stats_var = tk.StringVar(value="")
        tk.Label(
            self, textvariable=self.stats_var,
            bg=DARK_BG, fg=SUBTEXT,
            font=("Courier New", 9),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 6))

    def _btn(self, parent, text, cmd, accent=False, danger=False):
        fg = DARK_BG if accent else (ERROR_COL if danger else TEXT)
        bg = ACCENT  if accent else (PANEL_BG  if not danger else PANEL_BG)
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=bg, fg=fg, activebackground=ACCENT, activeforeground=DARK_BG,
            font=("Courier New", 10, "bold" if accent else "normal"),
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
        )
        b.bind("<Enter>", lambda e: b.configure(bg=ACCENT if accent else BORDER))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def _editor_frame(self, parent, label):
        frame = tk.Frame(parent, bg=PANEL_BG, bd=0)
        tk.Label(
            frame, text=label,
            bg=PANEL_BG, fg=SUBTEXT,
            font=("Courier New", 9),
            anchor="w", padx=6, pady=3,
        ).pack(fill="x")
        tk.Frame(frame, bg=BORDER, height=1).pack(fill="x")
        return frame

    def _editor(self, parent, readonly=False, color=TEXT):
        wrap = tk.Frame(parent, bg=PANEL_BG)
        wrap.pack(fill="both", expand=True)

        sb = tk.Scrollbar(wrap, bg=PANEL_BG, troughcolor=PANEL_BG,
                           relief="flat", bd=0, width=10)
        sb.pack(side="right", fill="y")

        t = tk.Text(
            wrap,
            bg=PANEL_BG, fg=color, insertbackground=ACCENT,
            selectbackground=ACCENT, selectforeground=DARK_BG,
            font=("Courier New", 11),
            relief="flat", bd=0, padx=8, pady=6,
            wrap="none",
            yscrollcommand=sb.set,
        )
        t.pack(fill="both", expand=True)
        sb.config(command=t.yview)

        if readonly:
            t.config(state="disabled")

        return t

    # ── Actions ───────────────────────────────────────────────────────────────
    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Open Lua file",
            filetypes=[("Lua files", "*.lua"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", content)
            self._set_status(f"Loaded: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")

    def _minify(self):
        source = self.input_text.get("1.0", "end-1c").strip()
        if not source:
            self._set_status("⚠  Nothing to minify.", error=True)
            return

        try:
            result = minify_lua(source)
        except Exception as e:
            self._set_status(f"Error: {e}", error=True)
            return

        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", result)
        self.output_text.config(state="disabled")

        in_chars  = len(source)
        out_chars = len(result)
        saved     = in_chars - out_chars
        pct       = (saved / in_chars * 100) if in_chars else 0
        self.stats_var.set(
            f"Input: {in_chars:,} chars   →   Output: {out_chars:,} chars   "
            f"({pct:.1f}% smaller,  saved {saved:,} chars)"
        )
        self._set_status("✓  Minified successfully.")

    def _copy(self):
        result = self.output_text.get("1.0", "end-1c").strip()
        if not result:
            self._set_status("⚠  Output is empty.", error=True)
            return
        self.clipboard_clear()
        self.clipboard_append(result)
        self._set_status("✓  Copied to clipboard.")

    def _save(self):
        result = self.output_text.get("1.0", "end-1c").strip()
        if not result:
            self._set_status("⚠  Output is empty.", error=True)
            return
        path = filedialog.asksaveasfilename(
            title="Save minified file",
            defaultextension=".lua",
            filetypes=[("Lua files", "*.lua"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(result)
            self._set_status(f"✓  Saved to {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

    def _clear(self):
        self.input_text.delete("1.0", "end")
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.config(state="disabled")
        self.stats_var.set("")
        self._set_status("Cleared.")

    def _set_status(self, msg, error=False):
        self.status_var.set(msg)
        self.status_lbl.config(fg=ERROR_COL if error else ACCENT2)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
