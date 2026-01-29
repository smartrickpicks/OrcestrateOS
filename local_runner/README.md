# local_runner: Offline Preview Harness (Governance Mode)

## Purpose
Provide a deterministic, offline method to preview the impact of semantic rules on example datasets without any network access.

## What It Does
- Loads base and optional patch config files
- Applies rules to example standardized datasets and optional QA packets
- Emits an sf_packet-like preview output for review

## What It Does NOT Do
- No runtime execution
- No external APIs or credentials
- No production parity guarantees

## Required Inputs
- config/config_pack.base.json
- optional config/config_pack.example.patch.json
- examples/standardized_dataset.example.json (or equivalent standardized input)
- optional examples/expected_outputs/qa_packet.example.json

## Governance Mode
- Offline preview only
- Deterministic results: same inputs produce the same outputs
- Intended for operator and reviewer validation of semantics prior to approval

## Example Commands (no network)
Preview with base only:
```
python3 local_runner/run_local.py \
  --base config/config_pack.base.json \
  --standardized examples/standardized_dataset.example.json \
  --out out/sf_packet.preview.json
```

Preview with base + patch:
```
python3 local_runner/run_local.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json \
  --standardized examples/standardized_dataset.example.json \
  --out out/sf_packet.preview.json
```

## Replit-Specific (Button-Run + Smoke Test)
- One-button run: .replit executes validate_config.py then run_local.py with repo defaults
- Explicit smoke test (strict diff):
```
bash scripts/replit_smoke.sh
```
  - Pass: exit 0 and message "OK: preview output matches expected (normalized)."
  - Fail: non-zero exit with a unified diff and guidance to fix determinism/schema or update expected output + CHANGELOG
- Allow diff temporarily (does not fail, still prints diff):
```
bash scripts/replit_smoke.sh --allow-diff
```

## Output
- A single file, e.g., `out/sf_packet.preview.json`, suitable for review alongside the patch.

## Determinism
- Given identical inputs, preview output must be identical. Any divergence indicates an input or configuration change.

## Status Meanings
- READY: Rule behaves as intended
- NEEDS_REVIEW: Ambiguous or partial outcome
- BLOCKED: Validation or conflict failure
