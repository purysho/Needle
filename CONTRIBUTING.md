# Contributing to Needle

## What we need most right now

- Bug reports with reproduction steps and platform details
- Platform-specific edge cases (macOS and Linux especially welcome)
- README corrections and documentation improvements
- Performance observations on large folders (index build time, index size, search latency)

## How to run from source

Requirements: Python 3.10+ with Tk support.

Windows:

```bash
pyw needle_desktop.pyw
```

macOS and Linux:

```bash
python3 needle_desktop.pyw
```

## How to run tests

```bash
python -m unittest discover -s tests -v
```

CI also checks that every source file compiles:

```bash
python -m compileall -q .
```

The tests cover the core modules and need no display. Window layout and
interaction are not covered by automated tests, so say in the pull request how
you checked a UI change by hand, and on which platform.

## Pull request checklist

- [ ] Tests pass locally on your platform
- [ ] New behaviour is covered by a test or the reason it cannot be is explained
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] No new runtime dependencies added (stdlib only at runtime)

## Code style

- Standard library only at runtime — no third-party packages in the core app
- Tkinter for UI
- Keep modules small and independently testable
- One concern per file
- Keep `needle/indexer.py` free of Tkinter imports so indexing and search stay testable without a display

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the modules fit together.

## Commit messages

Explain the reasoning and the alternative rejected. A subject line that states
the change is fine; a body that only restates the diff is not useful.

## Reporting security issues

See [SECURITY.md](SECURITY.md). Do not put exploit details in a public issue.
