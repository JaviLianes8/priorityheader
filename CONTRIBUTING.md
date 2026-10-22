# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
python scripts/fetch_upstream.py
```

The second command downloads the RFCs, the IANA registry and the structured field test
corpus listed in `tests/upstream/MANIFEST.json` and checks their hashes. They are kept out
of the repository; the tests that need them skip until they are fetched.

`pip install http-sf hyperframe aioquic` adds the independent implementations the
tests compare against; they are never runtime dependencies. `PRIORITYHEADER_E2E=1` builds
the wheel and drives it from a fresh virtual environment, and `PRIORITYHEADER_E2E_PYPI=1`
also upgrades the release on PyPI in place.

## Before you open a pull request

- Keep public API in `src/priorityheader/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests inject time, disk and network; they
  never touch the real thing.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
