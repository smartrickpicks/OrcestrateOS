# examples/README

## Purpose
Explain how example datasets and QA packets are used for offline preview only within the Semantic Control Board.

## What Examples Represent
- Minimal, synthetic rows that exercise specific rules and edge cases
- Canonical field names and shapes consistent with the base config
- Deterministic inputs for repeatable, auditable previews

## What Examples Do Not Represent
- Production data volume, diversity, or distribution
- External system behavior or API responses
- Performance characteristics or operational constraints

## Rules for Adding New Examples
- Use synthetic, non-identifying values only
- Include the smallest set of fields necessary to demonstrate the rule
- Provide a short companion note describing intent and expected outcomes
- Keep files small and focused; avoid large CSVs or verbose JSON
- Maintain stable ordering to ensure deterministic diffs
- Update expected_outputs to reflect new examples and outcomes

## Why Examples Are Synthetic and Minimal
- Prevent accidental inclusion of credentials or proprietary data
- Keep previews fast, reproducible, and easy to review
- Make diffs readable and auditable for rule changes

## Baseline vs Edge-Case Packs
- Baseline pack
  - Dataset: examples/standardized_dataset.example.json
  - Expected: examples/expected_outputs/sf_packet.example.json
  - Use for standard governance runs and routine smoke tests.
- Edge-case pack
  - Dataset: examples/standardized_dataset.edge_cases.json
  - Expected: examples/expected_outputs/sf_packet.edge_cases.json
  - Use to audit boundary conditions: missing contract_key, missing file_url, file_name-only join, and missing target-row joins.
- Selection
  - Default smoke uses the baseline pack.
  - To target edge-case pack: `bash scripts/replit_smoke.sh --edge` (strict by default; add `--allow-diff` only for exploratory checks).
