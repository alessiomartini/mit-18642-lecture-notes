#!/usr/bin/env python3
"""Local study server: serves study/out/ and a tiny JSON notes API backed by study/notes.db (sqlite).

  python study/server.py [--port 8642]     then open http://127.0.0.1:8642/ch04.html

Bound to 127.0.0.1 only. POSTs must be application/json (blocks cross-site form posts) and the
Host header must be local (blocks DNS rebinding).
"""
import argparse, json, re, sqlite3, sys
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
DB = HERE / "notes.db"
KINDS = ("note", "question", "solution")
SCHEMA = """CREATE TABLE IF NOT EXISTS notes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, chapter TEXT NOT NULL, paragraph_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('note','question','solution')), text TEXT NOT NULL,
  video_time REAL, video_id TEXT, created_at TEXT NOT NULL, imported_at TEXT)"""


def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; c.execute(SCHEMA); return c


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a):
        if "/api/" in (a[0] if a else ""): super().log_message(fmt, *a)

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def _local(self):
        if not re.fullmatch(r"(127\.0\.0\.1|localhost)(:\d+)?", self.headers.get("Host", "")):
            self._json({"error": "bad host"}, 403); return False
        return True

    def end_headers(self):
        self.send_header("Cache-Control", "no-store"); super().end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/notes":
            if not self._local(): return
            ch = parse_qs(u.query).get("chapter", [None])[0]
            with db() as c:
                rows = c.execute("SELECT * FROM notes WHERE (?1 IS NULL OR chapter=?1) ORDER BY id", (ch,)).fetchall()
            return self._json([dict(r) for r in rows])
        if u.path == "/":
            self.send_response(302); self.send_header("Location", "/index.html"); self.end_headers(); return
        super().do_GET()

    def _body(self):
        if not self._local(): return None
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            self._json({"error": "json only"}, 415); return None
        try: return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except ValueError: self._json({"error": "bad json"}, 400); return None

    def do_POST(self):
        if urlparse(self.path).path != "/api/notes": return self._json({"error": "not found"}, 404)
        d = self._body()
        if d is None: return
        try:
            ch, pid, kind, text = (str(d[k]) for k in ("chapter", "paragraph_id", "kind", "text"))
            assert kind in KINDS and text.strip() and ch and pid
            vt = float(d["video_time"]) if d.get("video_time") is not None else None
        except (KeyError, AssertionError, ValueError):
            return self._json({"error": "need chapter, paragraph_id, kind in %s, text" % (KINDS,)}, 400)
        created = str(d.get("created_at") or datetime.now(timezone.utc).isoformat(timespec="seconds"))
        with db() as c:
            cur = c.execute("INSERT INTO notes(chapter,paragraph_id,kind,text,video_time,video_id,created_at) VALUES(?,?,?,?,?,?,?)",
                            (ch, pid, kind, text, vt, d.get("video_id"), created))
            row = c.execute("SELECT * FROM notes WHERE id=?", (cur.lastrowid,)).fetchone()
        self._json(dict(row), 201)

    def do_DELETE(self):
        m = re.fullmatch(r"/api/notes/(\d+)", urlparse(self.path).path)
        if not m or not self._local(): return self._json({"error": "not found"}, 404)
        with db() as c:  # imported notes are already in the LaTeX: keep the row as a record
            n = c.execute("DELETE FROM notes WHERE id=? AND imported_at IS NULL", (int(m.group(1)),)).rowcount
        self._json({"deleted": n})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8642); a = ap.parse_args()
    out = HERE / "out"
    if not out.exists(): sys.exit("study/out/ missing: run  python study/build.py  first")
    db().close()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), partial(Handler, directory=str(out)))
    print(f"http://127.0.0.1:{a.port}/ch04.html   (Ctrl+C to stop; notes in {DB})")
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
