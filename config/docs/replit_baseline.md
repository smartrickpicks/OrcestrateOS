# Replit Golden Run Baseline (Non‑normative)

Purpose
- Capture the verified Replit environment details and output hash for a strict-pass smoke run.
- Provide a stable reference for future diffs and audits.

Scope
- Informational only; does not change semantics or execution rules.
- No secrets. Record placeholders if sensitive values are involved elsewhere.

Checklist (complete in order)
- [x] TASK-18 strict smoke test passed (no `--allow-diff`)
- [x] `out/sf_packet.preview.json` created
- [x] SHA256 recorded
- [x] Environment details recorded

Environment Details
- Date (UTC): 2026-01-30 00:23 UTC
- Replit workspace type: Default Nix Python
- Python version: Python 3.12.12
- Platform: Linux-6.14.11-x86_64-with-glibc2.40
- Repo commit (short SHA): b78930f

Config Versions
- base.version: v0.1.0
- patch.base_version: v0.1.0

SHA256 Verification
Compute and record the SHA256 for determinism.

Option A (python stdlib only):
```
python3 - <<'PY'
import hashlib, sys
p = 'out/sf_packet.preview.json'
h = hashlib.sha256()
with open(p, 'rb') as f:
    for chunk in iter(lambda: f.read(8192), b''):
        h.update(chunk)
print(h.hexdigest())
PY
```

Option B (if available):
```
shasum -a 256 out/sf_packet.preview.json | awk '{print $1}'
```

Recorded Hashes
- out/sf_packet.preview.json (SHA256): bea0af0e24f3994b80ac84bfdf6aaa4241b18ed045c0d1ef691bee8c55679452
- examples/expected_outputs/sf_packet.example.json (SHA256): f37d2dfe25829da2064b63c1012bb51d31f52ec7672098d20c8943d9dc2c8105

Result
- Status: PASS
- Notes: Deterministic output ordering fix applied (v0.1.2). Entries with contract_key now sort before entries without.
