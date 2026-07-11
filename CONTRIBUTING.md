# Contributing

Thanks for considering a contribution.

## Ground rules

- Keep examples generic. Do not commit real tokens, MAC addresses, private hostnames, Tailnet names, router URLs, production paths, or generated private snapshots.
- Keep the project local-first and kiosk-safe.
- Prefer small focused pull requests.
- Add or update tests for behavior changes.
- Update README/docs when user-facing behavior changes.
- Do not claim hardware or production validation unless it was actually run and documented.

## Development workflow

```bash
./scripts/smoke_test.sh
```

Run the repository's smoke test before opening a pull request.

For Python repositories, also verify editable installation when applicable:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Documentation standard

Docs should answer:

- What problem does this solve?
- Who is it for?
- What is verified?
- What is not verified yet?
- How do I run the smallest useful example?
- What are the safety boundaries?

## Pull request checklist

- [ ] Smoke tests pass.
- [ ] No secrets/private identifiers are included.
- [ ] README/docs updated if needed.
- [ ] Verification status is honest.
- [ ] No production kiosk/device assumptions are added silently.
