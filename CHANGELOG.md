# Changelog

All notable changes to Needle are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, `docs/V1_RELEASE_CHECKLIST.md` and `docs/RECORDING_GUIDE.md`.
- README: a comparison with the well-known alternatives, and links to the rest of the Depot suite.

### Changed
- `SECURITY.md` now states supported versions, response times and the threat model.
- The bug report form asks for the run method and the expected behaviour.

## [1.2.1] - 2026-09-26

### Fixed
- UTF-16 text files (common on Windows) were skipped as binary.
- Windows-1252 and Latin-1 files of even length were decoded as UTF-16 and indexed as noise. UTF-16 is now used only when the file starts with a byte-order mark.

### Added
- Behavioural tests covering the areas above and the rest of the core.

## [1.2.0] - 2026-09-26

### Added
- Release builds for macOS (Apple Silicon) and Linux (x86_64) alongside Windows, with one `SHA256SUMS.txt` per release.
- `--root PATH` and `--query TEXT` arguments that index a workspace and run a search on launch, used by Switchyard's tool handoff.
- The application icon, which the Windows executable was missing.
- A screenshot of the running app in the README.

### Changed
- CI builds the macOS and Linux packages on every push.

## [1.1.0] - 2026-09-16

### Added
- Polished public release documentation and screenshot.
- Cross-platform CI checks plus Windows executable build artifact.
- Automated tagged GitHub Release workflow with SHA256 checksum.
- Issue templates and security/reporting guidance.

### Current product
- Build and update local file indexes
- Fast filename and content search
- Exact-phrase and typo-tolerant search
- Browse indexed files by extension
- Open or reveal results directly
- Portable local JSON indexes
