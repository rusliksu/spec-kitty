# Test Sanitation Workflow Evidence

Evidence commit: `f527f8733b87d567957b771101405478309b8b70`  
Environment: macOS host; Python 3.11 mission .venv; integrated lane f527f8733; exact commands and raw receipt hashes below

## Repository and cross-repository gates

| Gate | Command | Result | Duration | Exit | Artifact |
|---|---|---|---:|---:|---|
| integrated full suite | PWHEADLESS=1 .venv/bin/pytest tests/ -n auto --dist loadfile -p no:cacheprovider --ignore=tests/sync/test_orphan_sweep.py | 35912 passed, 88 skipped, 4 xfailed | 1136.45 | 0 | sha256:b15d569a24468673fd808fe09aae01741c40b961c75dbe5885eb76865343e35c |
| serial orphan sweep | .venv/bin/pytest tests/sync/test_orphan_sweep.py | 9 passed | 15.01 | 0 | sha256:5356646b |
| Ruff | .venv/bin/ruff check . | All checks passed | 0 | 0 | sha256:82b3e6a6 |
| project mypy | .venv/bin/mypy src | 10 redundant-cast errors in six files identical to origin/main | 0 | 1 | sha256:55a71953 |
| contract | SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract/ -v | 292 passed, 3 skipped | 24.8 | 0 | sha256:ea496739 |
| architecture | .venv/bin/pytest tests/architectural/ -v | 869 passed, 2 skipped, 2 xfailed | 643.47 | 0 | sha256:69ecc698 |
| sibling E2E | SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest scenarios/ -v | 3 passed, 1 xfailed, 2 failed; daemon source/executable boundary mismatch | 127.14 | 1 | sha256:d0bbcba0 |

## Integrated platform evidence

| Platform | Workflow/job | Commit | Result | URL |
|---|---|---|---|---|
| Linux | exact integrated #3283 publication | f527f8733b87d567957b771101405478309b8b70 | NOT RUN: exact-commit remote evidence absent | https://github.com/Priivacy-ai/spec-kitty/pull/3285 |
| macOS | exact integrated #3283 publication | f527f8733b87d567957b771101405478309b8b70 | NOT RUN: WP02 local proof predates integrated commit | https://github.com/Priivacy-ai/spec-kitty/pull/3285 |
| Windows | exact integrated #3283 publication | f527f8733b87d567957b771101405478309b8b70 | NOT RUN: exact-commit remote evidence absent | https://github.com/Priivacy-ai/spec-kitty/pull/3285 |

## Fresh-clone starts

| Run | Commit | Publication/body proof | Result | Artifact |
|---:|---|---|---|---|
| 1 | WP02 integrated dependency | progress 0%-100%; JUnit tests=37455 | published one valid venv; no bootstrap cascade | raw/wp02-parallel-clean-starts.txt sha256:29e5808e45becb085f4771e6fb89880a328ebc00d918caa7e55ac03e2d937fd4 |
| 2 | WP02 integrated dependency | 3553 passed cases; controlled SIGINT after body-start oracle | published one valid venv; no bootstrap cascade | raw/wp02-parallel-clean-starts.txt sha256:29e5808e45becb085f4771e6fb89880a328ebc00d918caa7e55ac03e2d937fd4 |
| 3 | WP02 integrated dependency | JUnit tests=7499, 0 failures/errors; controlled SIGINT | published one valid venv; no bootstrap cascade | raw/wp02-parallel-clean-starts.txt sha256:29e5808e45becb085f4771e6fb89880a328ebc00d918caa7e55ac03e2d937fd4 |
