from __future__ import annotations
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import os
import subprocess
import threading
import time
import webbrowser

from .indexer import SearchIndex


class NeedleHandler(SimpleHTTPRequestHandler):
    index: SearchIndex = None
    index_path: Path = None
    web_root: Path = None
    lock: threading.RLock = None

    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/search":
            qs = parse_qs(parsed.query, keep_blank_values=True)
            q = qs.get("q", [""])[0]
            ext = qs.get("ext", [""])[0] or None
            raw_limit = qs.get("limit", [""])[0]
            if raw_limit:
                try:
                    limit = min(max(int(raw_limit), 1), 20000)
                except ValueError:
                    limit = 50
            else:
                # Browse mode returns all matching files. Ranked search remains bounded.
                limit = None if not q.strip() else 50

            with self.lock:
                payload = self.index.search(q, limit=limit, ext=ext)
            payload["count"] = len(payload["results"])
            return self._json(payload)

        if parsed.path == "/api/stats":
            with self.lock:
                return self._json(self.index.stats())

        if parsed.path in ("/api/open", "/api/reveal"):
            qs = parse_qs(parsed.query)
            requested = qs.get("path", [""])[0]
            with self.lock:
                allowed = requested in self.index.data.get("docs", {})
            if not requested or not allowed:
                return self._json({"ok": False, "message": "Path is not in the active Needle index."}, 403)
            p = Path(requested)
            if not p.exists():
                return self._json({"ok": False, "message": "File no longer exists."}, 404)
            try:
                action = "reveal" if parsed.path.endswith("reveal") else "open"
                _open_local_file(p, reveal=(action == "reveal"))
                return self._json({"ok": True, "action": action})
            except Exception as exc:
                return self._json({"ok": False, "message": str(exc)}, 500)

        return super().do_GET()

    def translate_path(self, path):
        parsed = urlparse(path)
        rel = parsed.path.lstrip("/") or "index.html"
        candidate = (self.web_root / rel).resolve()
        try:
            candidate.relative_to(self.web_root.resolve())
        except ValueError:
            return str(self.web_root / "index.html")
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.exists():
            candidate = self.web_root / "index.html"
        return str(candidate)

    def log_message(self, fmt, *args):
        pass


def _windows_path(path: Path) -> str:
    try:
        return subprocess.check_output(["wslpath", "-w", str(path)], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return str(path)


def _open_local_file(path: Path, reveal: bool = False):
    """Open/reveal only a path already validated against the active index."""
    if os.name == "nt":
        if reveal:
            subprocess.Popen(["explorer.exe", "/select,", str(path)])
        else:
            os.startfile(str(path))  # type: ignore[attr-defined]
        return

    release = os.uname().release.lower()
    if "microsoft" in release or "wsl" in release:
        win = _windows_path(path)
        if reveal:
            subprocess.Popen(["explorer.exe", f"/select,{win}"])
        else:
            subprocess.Popen(["cmd.exe", "/C", "start", "", win])
        return

    target = path.parent if reveal else path
    subprocess.Popen(["xdg-open", str(target)])


def _watch_loop(index: SearchIndex, index_path: Path, lock: threading.RLock, interval: int):
    roots = list(index.data.get("roots", []))
    if not roots:
        print("Background indexing disabled: this index has no recorded roots.")
        return
    print(f"Background indexing enabled every {interval}s.")
    while True:
        time.sleep(interval)
        try:
            with lock:
                stats = index.build(roots)
                if stats.changed or stats.removed:
                    index.save(index_path)
                    print(
                        f"[watch] updated: changed={stats.changed:,} "
                        f"removed={stats.removed:,} scanned={stats.scanned:,}",
                        flush=True,
                    )
        except Exception as exc:
            print(f"[watch] update failed: {exc}", flush=True)


def serve(index_path: str | Path, port: int = 8790, open_browser: bool = True, watch_interval: int = 0):
    index_path = Path(index_path).expanduser().absolute()
    idx = SearchIndex.load(index_path)
    web = Path(__file__).resolve().parent.parent / "web"
    lock = threading.RLock()

    NeedleHandler.index = idx
    NeedleHandler.index_path = index_path
    NeedleHandler.web_root = web
    NeedleHandler.lock = lock

    server = ThreadingHTTPServer(("127.0.0.1", port), NeedleHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"Needle V1.2 is serving {idx.doc_count:,} documents at {url}")
    print("Press Ctrl+C to stop.")

    if watch_interval > 0:
        threading.Thread(
            target=_watch_loop,
            args=(idx, index_path, lock, watch_interval),
            daemon=True,
        ).start()

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
