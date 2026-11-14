# Architecture

## Entry point

`needle_desktop.pyw` — parses `--root` and `--query`, constructs the main
window, starts the Tk event loop. No business logic here.

With `--root PATH`, Needle builds an index of that folder into
`~/.needle/switchyard-handoff.json` and, if `--query` was given, runs that
search once the build finishes. Switchyard uses this to hand a workspace to
Needle.

## Module layout

| Module | Responsibility |
|---|---|
| `needle_desktop.pyw` | Entry point, argument parsing, Switchyard handoff |
| `needle_ui.py` | Tkinter window: index controls, search box, paged results, snippet preview, open/reveal |
| `needle/indexer.py` | `SearchIndex`: walking folders, decoding text, building postings, ranking, typo suggestions, snippets. No Tkinter imports |
| `needle/server.py` | Optional local HTTP server that serves an index to a browser on `127.0.0.1`. Not used by the desktop app |
| `tests/` | Unit and behavioural tests for `needle/indexer.py` |
| `docs/` | Documentation and screenshots |
| `assets/` | Icons |

## Index model

An index is a single JSON document (`INDEX_VERSION = 1`) holding the indexed
roots, one entry per document (path, size, modification time, extension and
term frequencies), and enough metadata to rebuild postings in memory.

- **Build.** `SearchIndex.build()` walks each root with `os.walk`, skipping
  hidden folders and a fixed set of build/cache folders (`node_modules`,
  `.venv`, `__pycache__`, …), and reads files whose extension is in
  `DEFAULT_EXTENSIONS`, up to 4 MB each.
- **Incremental update.** A file whose size and modification time match the
  previous index is carried over without being re-read.
- **Decoding.** UTF-16 only with a byte-order mark; otherwise UTF-8, then
  Windows-1252, then Latin-1. Files that still look binary are skipped.
- **Search.** Postings, document frequencies and average length are built lazily
  on first search (`_prepare()`). Queries are tokenised; quoted text is an exact
  phrase. Ranking is BM25-style. With typo tolerance on, an unknown term is
  expanded to close matches from the vocabulary (`difflib`) at a reduced weight.
- **Browse.** An empty query lists indexed files, optionally filtered by
  extension.

## State storage

Indexes are saved wherever the user chooses in the save dialog; Needle has no
fixed data folder. The one exception is `~/.needle/switchyard-handoff.json`,
written only when launched with `--root`.

`SearchIndex.save()` writes atomically: JSON is written to `<name>.tmp`, then
renamed over the target with `Path.replace()`, so an interrupted save leaves the
previous index intact.

## Threading model

The UI runs on the main thread. Loading an index, building or updating one, and
searching each run on a daemon `threading.Thread`; `App.busy` stops a second
build from starting while one runs.

Each worker hands its result back with `root.after(0, callback)`, called from
the worker thread. This works with the Tcl builds shipped with CPython on all
three platforms, but Tkinter does not guarantee that `after()` is safe to call
from another thread. Moving to a `queue.Queue` polled by an `after()` timer on
the main thread is the documented direction and is tracked for v1.

Auto-update, when enabled, re-runs an incremental update every 60 seconds via
`after()`.

## CI

Every push and pull request (`.github/workflows/ci.yml`):

- Unit tests and `compileall` on Ubuntu and Windows, Python 3.10 and 3.12
- A Windows executable build with a size check, uploaded as an artifact
- macOS and Linux PyInstaller packages, each launched by
  `.github/scripts/launch-check.sh` to prove it starts

Tagged releases (`v*`, `.github/workflows/release.yml`): tests, Windows, macOS
and Linux builds, optional code signing when the signing secrets exist, one
`SHA256SUMS.txt`, and a GitHub Release.

## Build

```bash
powershell -ExecutionPolicy Bypass -File ./build-windows.ps1
```

Output: `dist/Needle.exe` — portable, no installer. The macOS and Linux build
commands are the `package` job in `ci.yml`.

## Dependency policy

No third-party packages at runtime. Standard library only. This keeps the
executable small, the build reproducible, and the attack surface minimal.
Build-time tools (PyInstaller) are the exception.
