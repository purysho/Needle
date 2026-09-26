<div align="center">
  <img src="assets/icon.png" width="132" alt="Needle icon">
  <h1>Needle</h1>
  <p><strong>A private local search engine for indexing, finding, browsing, and opening files on your computer.</strong></p>
  <p>
    <a href="https://github.com/purysho/Needle/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/purysho/Needle/actions/workflows/ci.yml/badge.svg"></a>
    <a href="https://github.com/purysho/Needle/releases"><img alt="Releases" src="https://img.shields.io/github/v/release/purysho/Needle?display_name=tag&sort=semver"></a>
    <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-202832.svg"></a>
    <a href="#download"><img alt="Status: beta" src="https://img.shields.io/badge/status-beta-C9A44C.svg"></a>
  </p>
  <p><strong>Download:</strong> <a href="https://github.com/purysho/Needle/releases/latest/download/Needle-Windows-x64.exe">Windows</a> · <a href="https://github.com/purysho/Needle/releases/latest/download/Needle-macOS-arm64.zip">macOS</a> · <a href="https://github.com/purysho/Needle/releases/latest/download/Needle-Linux-x86_64.tar.gz">Linux</a> · <a href="#run-from-source">Run from source</a> · <a href="https://github.com/purysho/Needle/issues">Report an issue</a></p>
</div>

![Needle searching an index of local projects, with ranked results and a matching snippet](docs/screenshot.png)

## What it does

- Build and update local file indexes
- Fast filename and content search
- Exact-phrase and typo-tolerant search
- Browse indexed files by extension
- Open or reveal results directly
- Portable local JSON indexes

## Download

| Platform | File |
|---|---|
| Windows 10/11 (x64) | [Needle-Windows-x64.exe](https://github.com/purysho/Needle/releases/latest/download/Needle-Windows-x64.exe) — portable, no installer |
| macOS (Apple Silicon) | [Needle-macOS-arm64.zip](https://github.com/purysho/Needle/releases/latest/download/Needle-macOS-arm64.zip) — unzip and move to Applications |
| Linux (x86_64) | [Needle-Linux-x86_64.tar.gz](https://github.com/purysho/Needle/releases/latest/download/Needle-Linux-x86_64.tar.gz) — extract and run `./Needle` |

Each [release](https://github.com/purysho/Needle/releases) is built from the tagged source by GitHub Actions and carries a `SHA256SUMS.txt`. The builds are not yet code-signed, so on first launch Windows SmartScreen may ask you to confirm ("More info" → "Run anyway"), and macOS may need you to Control-click the app and choose **Open**.

**Status: beta.** Needle does what this README describes and is covered by CI on Windows, macOS and Linux, but it is young: expect rough edges, and please [report them](https://github.com/purysho/Needle/issues).

## Run from source

Requirements: Python 3.10+ with Tk support.

```powershell
pyw needle_desktop.pyw
```

The application uses Python's standard library at runtime.

## Build a standalone Windows executable

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Output:

```text
dist\Needle.exe
```

## Privacy

Index creation and searching happen locally. Needle does not need a hosted search service or account.

## Scope

Needle targets personal/local file discovery rather than enterprise document management. Search is deliberately lightweight and deterministic.

## Release process

- Every push runs tests/compile checks and builds a Windows executable artifact.
- Tags matching `v*` build the executable again, compute SHA256, and publish both files to GitHub Releases.
- See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

MIT
