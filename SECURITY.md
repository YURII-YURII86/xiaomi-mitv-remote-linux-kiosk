# Security Policy

## Supported versions

Security fixes are handled on the `main` branch and the latest public release unless a repository-specific README states otherwise.

## Reporting a vulnerability

Please do **not** open a public issue for sensitive vulnerabilities.

Open a private GitHub security advisory when available, or contact the maintainer through GitHub with a minimal description of the impact and affected repository.

Include:

- repository name;
- affected version or commit;
- reproduction steps;
- expected impact;
- whether any secret, token, MAC address, host name, or private network path is involved.

## Local-first threat model

These projects are designed for local Linux kiosk/dashboard environments. They should not be exposed directly to the public internet without an additional security model.

Default principles:

- no secrets in browser-facing files;
- no real tokens or private hostnames in examples;
- localhost-only services unless explicitly documented;
- preview/dry-run before mutation;
- checkpoint before apply;
- hardware/production validation only with explicit approval.

## Production hardware safety

Do not run experimental validation against a live production kiosk, Intel Stick, signage player, or appliance unless the operator explicitly approves that exact test. Prefer fresh clones, CI, dry-runs, disposable VMs, or non-production hardware.
