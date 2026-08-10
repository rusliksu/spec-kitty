# Quickstart: Sanitation Verification

All commands run from repository root. Evidence captures exact environment and exit status.

## 1. Validate inventory and ledger

The mission-local auditor performs AST/ignore discovery and invokes pytest with an in-process collection plugin that records deterministic nodeids, parent source functions, effective markers, deselection, skips, hook errors, and collection states. JUnit is not used as a collection inventory.

```bash
.venv/bin/python kitty-specs/assertive-test-suite-sanitation-01KZME3P/evidence/audit.py snapshot \
  --tests tests \
  --output kitty-specs/assertive-test-suite-sanitation-01KZME3P/evidence/raw/head-census.json
.venv/bin/python kitty-specs/assertive-test-suite-sanitation-01KZME3P/evidence/audit.py validate \
  --census kitty-specs/assertive-test-suite-sanitation-01KZME3P/evidence/raw/head-census.json \
  --shards kitty-specs/assertive-test-suite-sanitation-01KZME3P/evidence/dispositions \
  --aggregate kitty-specs/assertive-test-suite-sanitation-01KZME3P/evidence/dispositions.yaml
```

## 2. Focused changed-cluster proof

Run the exact commands recorded in each ledger row. A causal `KEEP` probe must reach Act and fail its intended oracle; a deletion probe must remain green after the alleged implementation fault or be dominated by the named survivor.

```bash
.venv/bin/pytest <changed-paths> -q -p no:cacheprovider
.venv/bin/mutmut run --paths-to-mutate <claimed-source-cluster>
```

## 3. Full repository gates

```bash
PWHEADLESS=1 .venv/bin/pytest tests/ -n auto --dist loadfile -p no:cacheprovider \
  --ignore=tests/sync/test_orphan_sweep.py
PWHEADLESS=1 .venv/bin/pytest tests/sync/test_orphan_sweep.py -q -p no:cacheprovider
.venv/bin/ruff check .
.venv/bin/mypy src
```

Repeat the frozen collection and changed-route workloads three times for base and HEAD. Do not reuse unlike cache/runner states.

Validate changed route ownership/selectors from the frozen manifest and attach the applicable Linux/macOS/Windows matrix results for platform-owned survivors. Accepted unresolved P0 owner routes are expected red and must match the recorded live known-red set exactly.

## 4. Mission-review hard gates

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract/ -v
.venv/bin/pytest tests/architectural/ -v
```

In sibling `spec-kitty-end-to-end-testing`:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest scenarios/ -v
```

## 5. Acceptance

Validate `evidence/final-report.md`, issue matrix, and ledger; then run canonical `spec-kitty next`, `accept`, `merge`, post-merge mission review, retrospective synthesis, push, and PR checks.
