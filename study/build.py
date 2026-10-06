#!/usr/bin/env python3
"""LaTeX chapter -> study/out/<chapter>.html  (stdlib only).

Why a custom converter: make4ht is installed, but the notes rely on paracol + tcolorbox + queued
right-column macros that tex4ht cannot follow; pandoc is not installed. This converter knows the
macros of lecture-notes/preamble.tex and nothing else. LaTeX stays the single source.

Usage:  python study/build.py [ch04]        (default ch04; any chNN-*.tex works)
"""
import hashlib, html, json, re, shutil, subprocess, sys, tempfile, unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "lecture-notes"
STUDY = ROOT / "study"
OUT = STUDY / "out"

# ---------------------------------------------------------------- global state
class S:  # one chapter at a time
    chap = 0; cnt = {}; used = set(); labels = {}; figs = []; leftovers = []
    sidenote = 0; answer = 0; eq = 0; sec = 0; sub = 0; videos = {}; warn = []

def reset(chap):
    S.chap = chap; S.cnt = {"def": 0, "exercise": 0, "figure": 0}; S.used = set(); S.figs = []
    S.leftovers = []; S.sidenote = 0; S.answer = 0; S.eq = 0; S.sec = 0; S.sub = 0; S.warn = []

# ---------------------------------------------------------------- aux labels / videos
def load_labels():
    lab = {}
    for f in list(NOTES.glob("build/**/*.aux")):
        for m in re.finditer(r"\\newlabel\{([^}@]+)@cref\}\{\{\[(\w+)\]\[[^\]]*\]\[[^\]]*\]([^}]*)\}", f.read_text(encoding="utf8", errors="ignore")):
            lab[m.group(1)] = (m.group(2), m.group(3))
    return lab

def load_videos():
    t = (NOTES / "preamble.tex").read_text(encoding="utf8")
    return {f"{y}@{l}": v for y, l, v in re.findall(r"\b(13|24)@([0-9]+(?:-[IVX]+)?)=([A-Za-z0-9_-]{11})", t)}

# ---------------------------------------------------------------- small helpers
def uid(prefix, text):
    h = hashlib.sha1(re.sub(r"\s+", " ", text.strip())[:90].encode()).hexdigest()[:7]
    base = f"{prefix}-{h}"; u = base; k = 2
    while u in S.used: u = f"{base}-{k}"; k += 1
    S.used.add(u); return u

def grab(s, i):
    """balanced {group} at/after i (skipping blanks) -> (content, next index); single token otherwise"""
    while i < len(s) and s[i] in " \t\n": i += 1
    if i >= len(s): return "", i
    if s[i] != "{": return s[i], i + 1
    d = 0; j = i
    while j < len(s):
        c = s[j]
        if c == "\\": j += 2; continue
        if c == "{": d += 1
        elif c == "}":
            d -= 1
            if d == 0: return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)

def grab_opt(s, i):
    """[optional] immediately at i -> (content or None, next index)"""
    if i < len(s) and s[i] == "[":
        d = 0; j = i
        while j < len(s):
            c = s[j]
            if c == "\\": j += 2; continue
            if c == "{": d += 1
            elif c == "}": d -= 1
            elif c == "]" and d == 0: return s[i + 1:j], j + 1
            j += 1
    return None, i

def env_end(s, i, name):
    """index of the matching \\end{name} (start) and its end, given i just after \\begin{name}"""
    pat = re.compile(r"\\(begin|end)\{" + re.escape(name) + r"\}"); d = 1
    for m in pat.finditer(s, i):
        d += 1 if m.group(1) == "begin" else -1
        if d == 0: return m.start(), m.end()
    raise ValueError("unmatched \\begin{%s}" % name)

def strip_comments(t):
    return "\n".join(re.sub(r"(?<!\\)%.*", "", l) for l in t.split("\n"))

def esc(t): return html.escape(t, quote=False)

def secs(t):
    p = [int(x) for x in t.split(":")]; r = 0
    for x in p: r = 60 * r + x
    return r

ACCENT = {"'": "\u0301", "`": "\u0300", '"': "\u0308", "^": "\u0302", "~": "\u0303"}
MATHENV = {"equation", "equation*", "align", "align*", "gather", "gather*", "multline*"}
IGNORE = {"small", "footnotesize", "scriptsize", "tiny", "normalsize", "large", "centering", "smallskip",
          "medskip", "bigskip", "noindent", "leavevmode", "par", "itshape", "bfseries", "raggedright",
          "newline", "clearpage", "hfill", "vspace", "qedhere"}

# ---------------------------------------------------------------- math
def math_clean(m):
    m = re.sub(r"\\label\{[^}]*\}|\\qedhere|\\nonumber", "", m)
    return m

def math_html(m, display):
    return ('\\[' if display else '\\(') + esc(math_clean(m)) + ('\\]' if display else '\\)')

# ---------------------------------------------------------------- inline TeX -> html
def ref_html(label):
    kind, num = S.labels.get(label, (None, None))
    if kind is None:
        S.warn.append("unresolved ref " + label); return '<span class="ref ext">??</span>'
    name = {"chapter": "Chapter", "section": "Section", "subsection": "Section", "definition": "Definition",
            "example": "Example", "exercise": "Exercise", "theorem": "Theorem", "proposition": "Proposition",
            "lemma": "Lemma", "corollary": "Corollary", "remark": "Remark", "figure": "Figure",
            "equation": "Eq.", "table": "Table", "appendix": "Appendix", "answer": "Answer"}.get(kind, kind.title())
    txt = f"{name} {num}" if kind != "equation" else f"Eq. ({num})"
    if label in S.anchors:
        return f'<a class="ref" href="#{label}">{txt}</a>'
    return f'<span class="ref ext" title="in another chapter">{txt}</span>'

def ts_html(y, l, t):
    key = f"{y}@{l}"; vid = S.videos.get(key)
    label = f"[&#9654;&#8202;20{y} L{l} @ {t}]"
    if not vid or not re.fullmatch(r"\d+(:\d+)*", t):
        return f'<span class="ts nov">{label}</span>'
    return (f'<a class="ts" href="https://youtu.be/{vid}?t={secs(t)}" data-k="{key}" data-v="{vid}" '
            f'data-t="{secs(t)}">{label}</a>')

def side_card(kind, body_html, tag=None, num=None):
    cls = {"note": "note", "feedback": "feedback", "feedbackerr": "feedbackerr"}[kind]
    t = f'<span class="tag t-{tag.lower()}">{tag}</span> ' if tag else ""
    n = f'<b class="sn-n">{num}</b> ' if num else ""
    return f'<div class="sc {cls}">{t}{n}{body_html}</div>'

def inline(s, sides=None):
    """-> html. Side-column items found in s (\\note, \\feedback) are appended to `sides`."""
    if sides is None: sides = []
    out = []; i = 0; n = len(s)
    def sub(x): return inline(x, sides)
    while i < n:
        c = s[i]
        if c == "$":
            j = i + 1
            while j < n and not (s[j] == "$" and s[j - 1] != "\\"): j += 1
            out.append(math_html(s[i + 1:j], False)); i = j + 1; continue
        if c == "\\":
            if i + 1 >= n: break
            d = s[i + 1]
            if d == "[":
                j = s.index("\\]", i); out.append(math_html(s[i + 2:j], True)); i = j + 2; continue
            if d == "(":
                j = s.index("\\)", i); out.append(math_html(s[i + 2:j], False)); i = j + 2; continue
            if not d.isalpha():
                i += 2
                if d == "\\": out.append("<br>")
                elif d in "&%$#_{}": out.append(d)
                elif d == ",": out.append("&#8201;")
                elif d in " ;": out.append(" ")
                elif d in ACCENT:
                    g, i2 = grab(s, i)
                    if g.startswith("\\") and g[1:].isalpha() is False: pass
                    ch = g[:1]
                    if ch == "\\": ch = ""  # \i etc not needed
                    out.append(unicodedata.normalize("NFC", ch + ACCENT[d]) + g[1:]); i = i2
                continue
            m = re.compile(r"[A-Za-z]+\*?").match(s, i + 1); name = m.group(0).rstrip("*"); j = m.end()
            if m.group(0).endswith("*") and name not in ("note", "feedback", "section", "subsection"): j -= 1
            if name == "begin":
                en, j2 = grab(s, j)
                if en in MATHENV:
                    e0, e1 = env_end(s, j2, en); body = s[j2:e0]; star = en.endswith("*"); base = en.rstrip("*")
                    if base == "equation":
                        if star: out.append(math_html(body, True))
                        else:
                            S.eq += 1; out.append(math_html(body + f"\\tag{{{S.chap}.{S.eq}}}", True))
                    else:
                        out.append(math_html("\\begin{aligned}" + body + "\\end{aligned}", True))
                    i = e1; continue
                S.leftovers.append("\\begin{%s}" % en); out.append(f'<span class="lx">\\begin{{{esc(en)}}}</span>'); i = j2; continue
            i = j
            if name in ("emph", "textit"): g, i = grab(s, i); out.append(f"<em>{sub(g)}</em>")
            elif name == "textbf": g, i = grab(s, i); out.append(f"<strong>{sub(g)}</strong>")
            elif name in ("texttt",): g, i = grab(s, i); out.append(f"<code>{sub(g)}</code>")
            elif name == "file": g, i = grab(s, i); out.append(f"<code>{esc(g)}</code>")
            elif name == "url": g, i = grab(s, i); out.append(f'<a href="{esc(g)}">{esc(g)}</a>')
            elif name == "href": u, i = grab(s, i); g, i = grab(s, i); out.append(f'<a href="{esc(u)}">{sub(g)}</a>')
            elif name in ("cref", "Cref", "ref"):
                g, i = grab(s, i); out.append(", ".join(ref_html(x.strip()) for x in g.split(",")))
            elif name == "eqref":
                g, i = grab(s, i); r = ref_html(g.strip()); out.append(r.replace("Eq. (", "(") )
            elif name == "label": g, i = grab(s, i)
            elif name == "paragraph": g, i = grab(s, i); out.append(f'<strong class="ph">{sub(g)}</strong>')
            elif name == "ts":
                a, i = grab(s, i); b, i = grab(s, i); t, i = grab(s, i); out.append(ts_html(a, b, t))
            elif name in ("note", "feedback"):
                star = plus = False
                if i < n and s[i] == "*": star = True; i += 1
                elif i < n and s[i] == "+": plus = True; i += 1
                g, i = grab(s, i); body = sub(g)
                if name == "note":
                    S.sidenote += 1; k = S.sidenote
                    tag = "DONE" if star else "SEEN" if plus else None
                    out.append(f'<sup class="sn">{k}</sup>'); sides.append(("s", side_card("note", body, tag, k)))
                else:
                    sides.append(("s", side_card("feedbackerr" if star else "feedback", body,
                                                 "FEEDBACK: ERROR" if star else "FEEDBACK")))
            elif name == "S": out.append("&sect;")
            elif name in ("ldots", "dots", "textellipsis"): out.append("&hellip;")
            elif name in ("quad", "qquad"): out.append("&emsp;")
            elif name in IGNORE:
                if name == "vspace": grab(s, i); i = grab(s, i)[1]
            else:
                S.leftovers.append("\\" + name); out.append(f'<span class="lx">\\{name}</span>')
            continue
        if c in "{}": i += 1; continue
        if c == "~": out.append("&nbsp;"); i += 1; continue
        if s.startswith("---", i): out.append("&mdash;"); i += 3; continue
        if s.startswith("--", i): out.append("&ndash;"); i += 2; continue
        if s.startswith("``", i): out.append("&ldquo;"); i += 2; continue
        if s.startswith("''", i): out.append("&rdquo;"); i += 2; continue
        if c == "`": out.append("&lsquo;"); i += 1; continue
        if c == "'": out.append("&rsquo;"); i += 1; continue
        out.append(esc(c)); i += 1
    return "".join(out)

# ---------------------------------------------------------------- block structure
NUMBERED = {  # name: (css class, shown name, counter, goes to side column)
    "definition": ("def", "Definition", "def", False), "theorem": ("thm", "Theorem", "def", False),
    "proposition": ("thm", "Proposition", "def", False), "lemma": ("thm", "Lemma", "def", False),
    "corollary": ("thm", "Corollary", "def", False), "remark": ("rem", "Remark", "def", False),
    "example": ("ex", "Example", "def", True), "sideexample": ("ex", "Example", "def", False),
    "exercise": ("exer", "Exercise", "exercise", False)}
PLAIN = {  # name: (css class, title, goes to side column)
    "intuition": ("intu", "Intuition", False), "finance": ("fin", "In finance", False),
    "casestudy": ("cs", "Case study", False), "keyformulas": ("key", "Key formulas", False),
    "sources": ("rem hdr", "Sources for this chapter", False), "secondary": ("sec", "Beyond the core", False),
    "mysolution": ("exer hdr", "My solution", False), "coursenote": ("rem hdr", "Course note", True),
    "history": ("hist hdr", "History", True), "aside": ("hist hdr", "Aside", True),
    "proof": ("pf", "Proof", True)}
BLOCKNAMES = set(NUMBERED) | set(PLAIN) | {"itemize", "enumerate", "figure", "tabularx", "answer", "paracol"}
PARA_END = re.compile(r"\n[ \t]*\n|\n[ \t]*\\(?:begin\{(?:%s)\}|section|subsection|subsubsection|chapter)"
                      % "|".join(re.escape(x) for x in BLOCKNAMES))

def first_label(body):
    m = re.search(r"\\label\{([^}]*)\}", body); return m.group(1) if m else None

def split_items(body):
    parts = []; d = 0; last = None; pos = 0
    for m in re.finditer(r"\\(begin|end)\{(?:itemize|enumerate)\}|\\item\b", body):
        t = m.group(0)
        if t.startswith("\\begin"): d += 1
        elif t.startswith("\\end"): d -= 1
        elif d == 0:
            if last is not None: parts.append(body[last:m.start()])
            last = m.end()
    if last is not None: parts.append(body[last:])
    return parts

def list_html(kind, opt, body, units):
    sides = []; lis = []
    for it in split_items(body):
        its = blocks(it, False); lis.append("".join(h for k, h in its if k == "m")); sides += [x for x in its if x[0] == "s"]
    cls = ""
    if kind == "enumerate":
        o = opt or ""
        cls = "pr" if re.search(r"\(?i\)?", o) and "a" not in o else "pa" if "a" in o else "pA" if "A" in o else ""
    tag = "ul" if kind == "itemize" else "ol"
    h = f'<{tag} class="{cls}">' + "".join(f"<li>{x}</li>" for x in lis) + f"</{tag}>"
    return h, sides

def add_btn(): return '<button class="add" title="Add a note here" aria-label="Add a note here">+</button>'

def table_html(body):
    body = body[grab(body, grab(body, 0)[1])[1]:]
    body = re.sub(r"\\(toprule|midrule|bottomrule)", "", body)
    rows = [r.strip() for r in re.split(r"\\\\", body) if r.strip()]
    h = '<div class="tw"><table>'
    for k, r in enumerate(rows):
        c = "th" if k == 0 else "td"
        h += "<tr>" + "".join(f"<{c}>{inline(x.strip())}</{c}>" for x in re.split(r"(?<!\\)&", r)) + "</tr>"
    return h + "</table></div>"

def figure_html(body):
    S.cnt["figure"] += 1; k = S.cnt["figure"]
    tk = re.search(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", body, re.S)
    cm = body.find("\\caption"); cap = ""
    if cm >= 0:
        cap, _ = grab(body, cm + len("\\caption"))
    lab = first_label(body); fid = lab or uid("fig", cap)
    name = f"{S.chapname}-fig{k}"
    S.figs.append((name, tk.group(0) if tk else "", fid))
    return (f'<figure class="u bx fig" id="{fid}"><img src="fig/{name}.svg" alt="Figure {S.chap}.{k}" loading="lazy">'
            f'<figcaption><strong>Figure {S.chap}.{k}.</strong> {inline(cap)}</figcaption></figure>')

def box(name, opt, body, units):
    """-> list of ('m'|'s', html)"""
    lab = first_label(body) or first_label(opt or "")
    sides = []
    topic = inline(opt, sides) if opt else ""
    if name in NUMBERED:
        cls, shown, ctr, side = NUMBERED[name]; S.cnt[ctr] += 1; num = f"{S.chap}.{S.cnt[ctr]}"
        want = S.labels.get(lab, (None, None))[1] if lab else None
        if want: num = want  # the PDF numbers right-column examples when typeset, not in source order
        title = f'<span class="ty">{shown.upper()} {num}</span>' + (f": {topic}" if topic else "")
    else:
        cls, shown, side = PLAIN[name]; num = ""
        if name == "proof":
            title = f'<span class="ty">{topic or "PROOF"}</span>' if topic else '<span class="ty">PROOF</span>'
        else:
            title = f'<span class="ty">{shown.upper()}</span>' + (f": {topic}" if topic else "")
    inner = blocks(body, units if not side else False)
    inner_m = "".join(h for k, h in inner if k == "m"); sides += [x for x in inner if x[0] == "s"]
    bid = lab or uid("bx", (opt or "") + body)
    if name == "secondary":
        h = f'<details class="u bx {cls}" id="{bid}" open><summary class="bt">&#9671; {title}</summary>{inner_m}</details>'
    else:
        extra = ""
        if name == "exercise":
            extra = f'<div class="mysol"><button class="solbtn" data-ex="{bid}">My solution</button></div>'
        h = f'<div class="u bx {cls}" id="{bid}"><div class="bt">{title}</div><div class="bb">{inner_m}</div>{extra}</div>'
    return [("s", h)] + sides if side else [("m", h)] + sides

def answer_html(q, topic, body):
    sides = []; S.sidenote += 1; k = S.sidenote
    parts = re.split(r"\\answerpart\{([^}]*)\}", body)
    S.answer += 1
    h = (f'<div class="sc note answer"><b class="sn-n">{k}</b> {inline(q, sides)}'
         f'<div class="ansbar">ANSWER {S.chap}.{S.answer}{": " + inline(topic) if topic else ""}</div>{inline(parts[0], sides)}')
    for t, b in zip(parts[1::2], parts[2::2]):
        S.answer += 1; h += f'<div class="ansbar">ANSWER {S.chap}.{S.answer}: {inline(t)}</div>{inline(b, sides)}'
    return [("s", h + "</div>")] + sides

def blocks(src, units=True):
    items = []; i = 0; n = len(src); ws = re.compile(r"\s*")
    while True:
        i = ws.match(src, i).end()
        if i >= n: break
        if src.startswith("\\begin{", i):
            m = re.compile(r"\\begin\{([^}]+)\}").match(src, i); name = m.group(1)
            if name not in MATHENV:
                if name == "paracol": i = grab(src, m.end())[1]; continue  # closed by the include hook, not in the file
                e0, e1 = env_end(src, m.end(), name); j = m.end()
                if name == "answer":
                    q, j = grab(src, j); topic, j = grab_opt(src, j)
                    items += answer_html(q, topic or "", src[j:e0]); i = e1; continue
                if name == "tabularx":
                    items.append(("m", table_html(src[j:e0]))); i = e1; continue
                opt, j = grab_opt(src, j) if name not in ("itemize", "figure") else (None, j)
                body = src[j:e0]
                if name in ("itemize", "enumerate"):
                    h, sd = list_html(name, opt, body, units)
                    items.append(("m", f'<div class="u p" id="{uid("p", body)}">{h}{add_btn()}</div>' if units else h)); items += sd
                elif name == "figure": items.append(("m", figure_html(body)))
                elif name in NUMBERED or name in PLAIN: items += box(name, opt, body, units)
                else:
                    S.warn.append("unknown env " + name); items.append(("m", f'<p class="lx">[{name}]</p>'))
                i = e1; continue
        if src.startswith("\\end{paracol}", i): i += len("\\end{paracol}"); continue
        m = re.compile(r"\\(chapter|section|subsection)(\*?)").match(src, i)
        if m:
            kind, star = m.group(1), m.group(2); t, j = grab(src, m.end())
            lab = None; lm = re.compile(r"\s*\\label\{([^}]*)\}").match(src, j)
            if lm: lab = lm.group(1); j = lm.end()
            num = ""
            if kind == "section" and not star: S.sec += 1; S.sub = 0; num = f"{S.chap}.{S.sec} "
            elif kind == "subsection" and not star: S.sub += 1; num = f"{S.chap}.{S.sec}.{S.sub} "
            lvl = {"chapter": 1, "section": 2, "subsection": 3}[kind]
            if kind == "chapter": num = f"Chapter {S.chap}. "; S.title = html.unescape(re.sub("<[^>]+>", "", inline(t)))
            hid = lab or uid("h", t)
            items.append(("m", f'<h{lvl} id="{hid}">{num}{inline(t)}</h{lvl}>')); i = j; continue
        mm = PARA_END.search(src, i); j = mm.start() if mm else n
        text = src[i:j]; i = j
        sides = []; h = inline(text.strip(), sides)
        if h.strip():
            items.append(("m", f'<p class="u p" id="{uid("p", text)}">{h}{add_btn()}</p>' if units else f"<p>{h}</p>"))
        items += sides
    return items

# ---------------------------------------------------------------- figures (TikZ -> svg)
FIG_PRE = r"""\documentclass{article}
\usepackage[T1]{fontenc}\usepackage{amsmath,amsthm,mathtools}\usepackage{newpxtext,newpxmath}\usepackage{bm}
\usepackage[paperwidth=40cm,paperheight=40cm,textwidth=15cm]{geometry}
\usepackage[dvipsnames]{xcolor}\usepackage{tikz}\usepackage{pgfplots}
%(extra)s
\usepackage[active,tightpage]{preview}\PreviewEnvironment{tikzpicture}\setlength\PreviewBorder{4pt}
\pagestyle{empty}\begin{document}
%(code)s
\end{document}
"""

def figure_svgs():
    pre = (NOTES / "preamble.tex").read_text(encoding="utf8")
    extra = "\n".join(l for l in pre.split("\n") if re.match(
        r"\\(definecolor|colorlet|usetikzlibrary|pgfplotsset|DeclareMathOperator|newcommand\{\\(R|N|E|Prob|Q|T|dd|ind|eqd)\})", l))
    FIG = OUT / "fig"; FIG.mkdir(parents=True, exist_ok=True)
    pdflatex, cairo = shutil.which("pdflatex"), shutil.which("pdftocairo")
    for name, code, fid in S.figs:
        code = re.sub(r"\\cref\{([^}]*)\}", lambda m: re.sub("<[^>]+>", "", ref_html(m.group(1))), code)
        code = re.sub(r"\\ts\{[^}]*\}\{[^}]*\}\{[^}]*\}", "", code)
        tex = FIG_PRE % {"extra": extra, "code": code}
        h = hashlib.sha1(tex.encode()).hexdigest()[:8]; dst = FIG / f"{name}.svg"; stamp = FIG / f"{name}.hash"
        if dst.exists() and stamp.exists() and stamp.read_text() == h: print("  figure", name, "(cached)"); continue
        if not (pdflatex and cairo and code): S.warn.append(f"figure {name}: no pdflatex/pdftocairo"); continue
        with tempfile.TemporaryDirectory() as td:
            Path(td, "f.tex").write_text(tex, encoding="utf8")
            r = subprocess.run([pdflatex, "-interaction=nonstopmode", "-halt-on-error", "f.tex"], cwd=td, capture_output=True, text=True)
            if r.returncode != 0 or not Path(td, "f.pdf").exists():
                S.warn.append(f"figure {name}: pdflatex failed"); print(r.stdout[-800:]); continue
            subprocess.run([cairo, "-svg", "f.pdf", str(dst)], cwd=td, check=True)
        stamp.write_text(h); print("  figure", name, "built")

# ---------------------------------------------------------------- page
def build(tex_path):
    S.labels = load_labels(); S.videos = load_videos()
    S.anchors = set(re.findall(r"\\label\{([^}]*)\}", strip_comments(tex_path.read_text(encoding="utf8"))))
    S.chapname = tex_path.name[:4]; chap = int(S.chapname[2:]); reset(chap)
    src = strip_comments(tex_path.read_text(encoding="utf8"))
    items = blocks(src)
    rows = []  # each row: [main html, [side html]]
    for k, h in items:
        if k == "m": rows.append([h, []])
        else:
            if not rows: rows.append(["", []])
            rows[-1][1].append(h)
    body = "".join(f'<div class="row"><div class="main">{m}</div><aside class="side">{"".join(s)}</aside></div>' for m, s in rows)
    OUT.mkdir(parents=True, exist_ok=True)
    figure_svgs()
    for f in ("study.css", "study.js"): shutil.copy(STUDY / "static" / f, OUT / f)
    ver = hashlib.sha1(b"".join((OUT / f).read_bytes() for f in ("study.css", "study.js"))).hexdigest()[:6]
    page = (STUDY / "static" / "page.html").read_text(encoding="utf8")
    page = (page.replace("%TITLE%", esc(S.title)).replace("%BODY%", body).replace("%VER%", ver)
            .replace("%CHAPTER%", S.chapname).replace("%VIDEOS%", json.dumps(S.videos)))
    (OUT / f"{S.chapname}.html").write_text(page, encoding="utf8")
    # index
    names = sorted(p.stem for p in OUT.glob("ch*.html"))
    (OUT / "index.html").write_text("<!doctype html><meta charset=utf-8><title>Study</title><link rel=stylesheet href=study.css><body class=idx><h1>Study HTML</h1><ul>"
        + "".join(f'<li><a href="{n}.html">{n}</a></li>' for n in names) + "</ul>", encoding="utf8")
    nts = len(re.findall(r'class="ts"', page)); nu = len(re.findall(r'class="u p"', page))
    lx = len(re.findall(r'class="lx"', page))
    raw = len(re.findall(r"\\begin|\\note|\\ts\b", re.sub(r"\\\(.*?\\\)|\\\[.*?\\\]", "", re.sub(r"<[^>]+>", "", body), flags=re.S)))
    print(f"{S.chapname}: {len(rows)} rows, {nu} paragraph units, {nts} timestamp buttons, {len(S.figs)} figures")
    print(f"leftover macros in text: {lx} unknown ({sorted(set(S.leftovers))}); raw \\begin/\\note/\\ts outside math: {raw}")
    for w in sorted(set(S.warn)): print("  warning:", w)
    print("->", OUT / f"{S.chapname}.html")

if __name__ == "__main__":
    ch = sys.argv[1] if len(sys.argv) > 1 else "ch04"
    f = sorted((NOTES / "chapters").glob(f"{ch}-*.tex"))
    if not f: sys.exit(f"no chapter {ch}")
    build(f[0])
