# V1 Release Checklist

Gates for changing the Needle README badge from `beta` to `stable`. A box is
ticked only when the gate has been checked against the repository, not when it
is expected to pass.

## Automated gates (CI must pass)
- [ ] All tests pass on Windows, macOS, Linux
- [ ] Packaged executable passes smoke test after re-download from GitHub Releases
- [ ] State file from previous release loads without error

What CI does today, and what each gate still needs:

- Unit tests run on Windows and Linux (Python 3.10 and 3.12). They do not run on
  macOS; the macOS job only builds the package and checks that it launches. The
  first gate needs `macos-latest` added to the test matrix.
- The macOS and Linux packages are launched in CI straight after they are built.
  Nothing downloads a published release asset and launches that. The second gate
  needs a job that runs after the release is published.
- Third gate: An index file written by the previous release loads without error. No test covers this yet.

## Documentation gates
- [x] README complete: description, download, "why not X", Depot link
- [x] CHANGELOG.md has at least two real version entries
- [x] CONTRIBUTING.md present
- [x] SECURITY.md present
- [x] docs/ARCHITECTURE.md present
- [x] docs/V1_RELEASE_CHECKLIST.md present (this file)

## Community gates
- [ ] At least one issue from an external user has been opened and responded to
- [ ] At least one release has been downloaded (verify via GitHub Releases traffic)
