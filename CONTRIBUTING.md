# Contributing

Thanks for taking a look! This repo is a small educational sandbox.

## Dev setup
- Python 3.11+
- `pip install -r requirements.txt`
- (optional) `pip install -U pytest ruff black pre-commit` and `pre-commit install`

## Checks
- Lint: `ruff check .`
- Format check: `black --check .`
- Tests: `pytest -q` (if you add tests)

## PR scope
Please keep PRs small and focused:
- Add tests for new behaviors.
- Preserve error codes (`NO_MAIN`, `NON_JSON_RETURN`, `EMPTY_OUTPUT`, `TIMEOUT`, etc.).
- Do not introduce network access in user code paths.
