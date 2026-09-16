<div align="center">
  <img src="assets/icon.png" width="140" alt="Needle icon">
  <h1>Needle</h1>
  <p><strong>A private local search engine for indexing, finding, browsing, and opening files on your computer.</strong></p>
</div>

Needle builds a lightweight local index over folders you choose and lets you search that index from a Windows desktop interface. It is designed for fast personal file discovery without sending your filenames or content to a hosted search service.

## Features

- Build and update local file indexes
- Search indexed files quickly
- Browse all indexed files of an extension with a blank query
- Open files directly from results
- Reveal files in the system file manager
- Read existing WSL-style `/mnt/c/...` paths used by compatible indexes
- Local HTTP server module for alternative integrations

## Run from source

Requirements: Windows and Python 3.10+.

```powershell
pyw needle_desktop.pyw
```

Needle uses Python's standard library and Tkinter; there are no third-party runtime dependencies.

## Build a standalone Windows executable

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Output:

```text
dist\Needle.exe
```

## Project structure

```text
Needle/
├── needle/
│   ├── indexer.py       # indexing and search engine
│   └── server.py        # optional local HTTP server
├── needle_desktop.pyw   # Tkinter desktop interface
├── build-windows.ps1
├── assets/
└── .github/workflows/
```

## Privacy

Needle is local-first. Index creation and searching happen on the user's machine. The desktop application does not need an external account or cloud search backend.

## Current scope

Needle is aimed at personal/local file search rather than enterprise document management. Search quality is intentionally lightweight and deterministic.

## Status

V1.1 — local indexing, searching, browsing, file opening, and Windows desktop packaging.
