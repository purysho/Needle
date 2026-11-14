# Security Policy

## Supported versions

The latest release is supported. Older releases do not receive security patches.

## Reporting a vulnerability

Open a GitHub issue titled `[SECURITY] <brief description>` that names the
affected area but leaves out exploit details, or contact the maintainer
directly through the GitHub profile if the details are sensitive.

Please do not disclose publicly until the maintainer has had a chance to
respond. We aim to acknowledge within 72 hours and patch within 14 days for
confirmed vulnerabilities.

## Threat model

Needle is a local desktop application. It does not:

- open listening network ports by default
- send telemetry, usage data, or crash reports
- require an account or sign-in
- upload files, code, or configuration to any server

Specific to Needle:

- The desktop app opens no network port. `needle/server.py` is an optional module that serves an index to a browser; it is not started by the desktop app and binds to `127.0.0.1` only.
- Indexes are plain JSON files saved wherever you choose; the only file Needle writes on its own is `~/.needle/switchyard-handoff.json`, the index built when it is launched with `--root`.

Vulnerabilities we care about:

- Command injection through user-supplied configuration or workflow inputs
- Unintended reads or writes outside declared scope
- State file corruption leading to data loss
- Reads outside the folders the user chose to index (for example by following links)
- An index file that is corrupted or lost by an interrupted save
- A crafted index file or indexed file name that makes Needle open or reveal something other than the selected result

Out of scope:

- Attacks requiring physical access to the machine
- Attacks that require an account on the machine that can already read or change your files
- Vulnerabilities in dependencies we do not control (report upstream)

## Scope

Needle targets personal/local file discovery rather than enterprise document management. Search is deliberately lightweight and deterministic.
