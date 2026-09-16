from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from collections import Counter, defaultdict
import difflib
import json
import math
import os
import re
import time
from typing import Iterable

INDEX_VERSION = 1

DEFAULT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".rst",
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
    ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".csv", ".tsv", ".html", ".htm", ".css", ".scss", ".less",
    ".rs", ".go", ".java", ".kt", ".kts", ".c", ".h", ".cc", ".cpp", ".hpp",
    ".sql", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
    ".xml", ".svg", ".vue", ".svelte",
}

IGNORE_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "target", "dist", "build", "out",
    ".next", ".nuxt", ".cache", ".parcel-cache",
    ".venv", "venv", "env", "__pycache__",
    ".idea", ".vscode",
    "coverage", ".pytest_cache", ".mypy_cache",
}


def runtime_path(path: str | Path) -> Path:
    """Translate a WSL /mnt/<drive>/... path when Needle runs natively on Windows."""
    raw = str(path)
    if os.name == "nt":
        m = re.match(r"^/mnt/([a-zA-Z])/(.*)$", raw)
        if m:
            drive, rest = m.groups()
            return Path(f"{drive.upper()}:\\" + rest.replace("/", "\\"))
    return Path(raw)

TOKEN_RE = re.compile(r"[\w][\w\-]{1,}", re.UNICODE)
PHRASE_RE = re.compile(r'"([^"]+)"')


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def _read_text(path: Path, max_bytes: int = 4_000_000) -> str | None:
    try:
        st = path.stat()
        if st.st_size > max_bytes:
            return None
        with path.open("rb") as fh:
            raw = fh.read()
        if b"\x00" in raw[:4096]:
            return None
        for enc in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                pass
        return None
    except (OSError, PermissionError):
        return None


def _iter_files(roots: list[Path]) -> Iterable[tuple[Path, os.stat_result]]:
    """Yield files plus cached stat metadata.

    Avoid Path.resolve() and repeated stat calls because they are particularly
    expensive on WSL paths mounted under /mnt/c.
    """
    seen = set()
    for root in roots:
        root = root.expanduser().absolute()
        if root.is_file():
            try:
                st = root.stat()
            except OSError:
                continue
            key = os.path.normcase(os.path.abspath(str(root)))
            if key not in seen:
                seen.add(key)
                yield root, st
            continue

        for current, dirs, names in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            base = Path(current)
            for name in names:
                p = base / name
                key = os.path.normcase(os.path.abspath(str(p)))
                if key in seen:
                    continue
                seen.add(key)
                try:
                    st = p.stat(follow_symlinks=False)
                except (OSError, PermissionError):
                    continue
                if not os.path.isfile(p):
                    continue
                yield p, st


@dataclass
class BuildStats:
    scanned: int = 0
    indexed: int = 0
    skipped: int = 0
    changed: int = 0
    removed: int = 0
    elapsed: float = 0.0


class SearchIndex:
    def __init__(self, data: dict | None = None):
        self.data = data or {
            "version": INDEX_VERSION,
            "created_at": time.time(),
            "updated_at": time.time(),
            "roots": [],
            "docs": {},
        }
        if self.data.get("version") != INDEX_VERSION:
            raise ValueError("Unsupported Needle index version")
        self._postings = None
        self._df = None
        self._avgdl = None

    @classmethod
    def load(cls, path: str | Path) -> "SearchIndex":
        with Path(path).open("r", encoding="utf-8") as fh:
            return cls(json.load(fh))

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, separators=(",", ":"))
        tmp.replace(p)

    def _invalidate(self):
        self._postings = self._df = self._avgdl = None

    def build(self, roots: list[str | Path], extensions: set[str] | None = None, progress=None) -> BuildStats:
        start = time.time()
        stats = BuildStats()
        exts = extensions or DEFAULT_EXTENSIONS
        root_paths = [runtime_path(r).expanduser().absolute() for r in roots]
        self.data["roots"] = [str(p) for p in root_paths]
        old_docs = self.data.get("docs", {})
        new_docs = {}
        last_progress = start

        for path, st in _iter_files(root_paths):
            stats.scanned += 1
            now = time.time()
            if progress and (stats.scanned == 1 or stats.scanned % 250 == 0 or now - last_progress >= 2.0):
                progress(stats, path, now - start)
                last_progress = now

            suffix = path.suffix.lower()
            if suffix not in exts:
                stats.skipped += 1
                continue

            fp = f"{st.st_size}:{st.st_mtime_ns}"
            key = os.path.abspath(str(path))
            old = old_docs.get(key)
            if old and old.get("fingerprint") == fp:
                new_docs[key] = old
                stats.indexed += 1
                continue

            if st.st_size > 4_000_000:
                stats.skipped += 1
                continue

            try:
                with path.open("rb") as fh:
                    raw = fh.read()
            except (OSError, PermissionError):
                stats.skipped += 1
                continue

            if b"\x00" in raw[:4096]:
                stats.skipped += 1
                continue

            text = None
            for enc in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    pass
            if text is None:
                stats.skipped += 1
                continue

            tokens = tokenize(text)
            if not tokens:
                stats.skipped += 1
                continue

            tf = Counter(tokens)
            new_docs[key] = {
                "path": key,
                "name": path.name,
                "ext": suffix,
                "size": st.st_size,
                "mtime": st.st_mtime,
                "fingerprint": fp,
                "length": len(tokens),
                "terms": dict(tf),
            }
            stats.indexed += 1
            stats.changed += 1

        stats.removed = len(set(old_docs) - set(new_docs))
        self.data["docs"] = new_docs
        self.data["updated_at"] = time.time()
        self._invalidate()
        stats.elapsed = time.time() - start
        if progress:
            progress(stats, None, stats.elapsed)
        return stats

    def _prepare(self):
        if self._postings is not None:
            return
        postings = defaultdict(list)
        df = defaultdict(int)
        lengths = []
        for doc_id, doc in self.data["docs"].items():
            lengths.append(doc["length"])
            for term, freq in doc["terms"].items():
                postings[term].append((doc_id, freq))
                df[term] += 1
        self._postings = postings
        self._df = df
        self._avgdl = (sum(lengths) / len(lengths)) if lengths else 0.0

    @property
    def doc_count(self) -> int:
        return len(self.data["docs"])

    @property
    def term_count(self) -> int:
        self._prepare()
        return len(self._postings)

    def _parse_query(self, query: str) -> tuple[list[str], list[str]]:
        phrases = PHRASE_RE.findall(query)
        outside = PHRASE_RE.sub(" ", query)
        terms = tokenize(outside)
        for phrase in phrases:
            terms.extend(tokenize(phrase))
        return terms, phrases

    def _suggest_terms(self, qtokens: list[str]) -> dict[str, list[str]]:
        self._prepare()
        vocab = list(self._postings.keys())
        out = {}
        for term in qtokens:
            if term in self._postings:
                continue
            matches = difflib.get_close_matches(term, vocab, n=3, cutoff=0.78)
            if matches:
                out[term] = matches
        return out

    def browse(self, ext: str | None = None, limit: int | None = None) -> list[dict]:
        docs = list(self.data["docs"].values())
        if ext:
            docs = [d for d in docs if d.get("ext") == ext]
        docs.sort(key=lambda d: (-float(d.get("mtime", 0)), d.get("path", "").lower()))
        if limit is not None:
            docs = docs[:limit]
        return [
            {
                "path": d["path"],
                "name": d["name"],
                "ext": d["ext"],
                "size": d["size"],
                "mtime": d["mtime"],
                "score": 0.0,
                "matched_terms": [],
                "snippet": "",
                "mode": "browse",
            }
            for d in docs
        ]

    def search(self, query: str, limit: int | None = 30, ext: str | None = None, typo_tolerance: bool = True) -> dict:
        self._prepare()
        qtokens, phrases = self._parse_query(query)

        if not qtokens and not phrases:
            return {
                "mode": "browse",
                "query": query,
                "results": self.browse(ext=ext, limit=limit),
                "suggestions": {},
                "phrases": [],
            }

        suggestions = self._suggest_terms(qtokens) if typo_tolerance else {}
        expanded: dict[str, list[tuple[str, float]]] = {}
        for term in qtokens:
            if term in self._postings:
                expanded[term] = [(term, 1.0)]
            elif typo_tolerance and term in suggestions:
                expanded[term] = [(m, 0.72) for m in suggestions[term]]
            else:
                expanded[term] = []

        N = max(self.doc_count, 1)
        k1, b = 1.5, 0.75
        scores = defaultdict(float)
        matched_terms = defaultdict(set)

        for _original, alternatives in expanded.items():
            for term, typo_weight in alternatives:
                plist = self._postings.get(term, [])
                n = self._df.get(term, 0)
                if not n:
                    continue
                idf = math.log(1 + (N - n + 0.5) / (n + 0.5))
                for doc_id, freq in plist:
                    doc = self.data["docs"][doc_id]
                    if ext and doc.get("ext") != ext:
                        continue
                    dl = doc["length"]
                    denom = freq + k1 * (1 - b + b * dl / max(self._avgdl, 1))
                    scores[doc_id] += typo_weight * idf * (freq * (k1 + 1) / denom)
                    matched_terms[doc_id].add(term)

        # Phrase search: require all phrase tokens in the document's term map
        # before touching the filesystem, then verify the exact substring.
        if phrases:
            verified = {}
            phrase_token_sets = [tokenize(p) for p in phrases]
            for doc_id, score in list(scores.items()):
                doc = self.data["docs"][doc_id]
                if not all(all(tok in doc["terms"] for tok in pts) for pts in phrase_token_sets):
                    continue
                text = _read_text(Path(doc["path"]))
                if text is None:
                    continue
                low = text.lower()
                if all(p.lower() in low for p in phrases):
                    verified[doc_id] = score * (1.0 + 0.45 * len(phrases))
            scores = defaultdict(float, verified)

        qlower = query.replace('"', "").lower().strip()
        unique_requested = max(len(set(qtokens)), 1)
        for doc_id in list(scores):
            doc = self.data["docs"][doc_id]
            name = doc["name"].lower()
            path = doc["path"].lower()
            if qlower and qlower in name:
                scores[doc_id] *= 1.8
            elif qlower and qlower in path:
                scores[doc_id] *= 1.25
            coverage = len(matched_terms[doc_id]) / unique_requested
            scores[doc_id] *= 0.75 + 0.5 * min(coverage, 1.0)

        ranked = sorted(scores.items(), key=lambda x: (-x[1], self.data["docs"][x[0]]["path"].lower()))
        if limit is not None:
            ranked = ranked[:limit]

        results = []
        snippet_terms = list(dict.fromkeys(qtokens))
        for doc_id, score in ranked:
            doc = self.data["docs"][doc_id]
            results.append({
                "path": doc["path"],
                "name": doc["name"],
                "ext": doc["ext"],
                "size": doc["size"],
                "mtime": doc["mtime"],
                "score": round(score, 4),
                "matched_terms": sorted(matched_terms[doc_id]),
                "snippet": make_snippet(Path(doc["path"]), snippet_terms, phrases=phrases),
                "mode": "search",
            })

        return {
            "mode": "search",
            "query": query,
            "results": results,
            "suggestions": suggestions,
            "phrases": phrases,
        }

    def stats(self) -> dict:
        self._prepare()
        by_ext = Counter(d["ext"] or "(none)" for d in self.data["docs"].values())
        total_size = sum(d["size"] for d in self.data["docs"].values())
        return {
            "documents": self.doc_count,
            "terms": self.term_count,
            "total_size": total_size,
            "roots": self.data.get("roots", []),
            "updated_at": self.data.get("updated_at"),
            "by_extension": dict(by_ext.most_common()),
        }


def make_snippet(path: Path, qtokens: list[str], phrases: list[str] | None = None, radius: int = 150) -> str:
    text = _read_text(runtime_path(path), max_bytes=4_000_000)
    if not text:
        return ""
    phrases = phrases or []
    low = text.lower()

    positions = []
    for phrase in phrases:
        p = low.find(phrase.lower())
        if p >= 0:
            positions.append((p, 0))
    for term in qtokens:
        p = low.find(term.lower())
        if p >= 0:
            positions.append((p, 1))
    pos = min(positions)[0] if positions else 0

    start = max(0, pos - radius)
    end = min(len(text), pos + radius * 2)
    line_start = text.rfind("\n", max(0, start - 80), pos)
    if line_start >= 0:
        start = line_start + 1
    line_end = text.find("\n", pos, min(len(text), end + 120))
    if line_end >= 0:
        end = line_end

    snippet = text[start:end].replace("\r", " ").replace("\n", " ")
    snippet = re.sub(r"\s+", " ", snippet).strip()
    if start:
        snippet = "… " + snippet
    if end < len(text):
        snippet += " …"
    return snippet
