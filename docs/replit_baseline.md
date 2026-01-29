# Replit Golden Run Baseline (Non‑normative)

Purpose
- Capture the verified Replit environment details and output hash for a strict-pass smoke run.
- Provide a stable reference for future diffs and audits.

Scope
- Informational only; does not change semantics or execution rules.
- No secrets. Record placeholders if sensitive values are involved elsewhere.

Checklist (complete in order)
- [ ] TASK-18 strict smoke test passed (no `--allow-diff`)
- [ ] `out/sf_packet.preview.json` created
- [ ] SHA256 recorded
- [ ] Environment details recorded

Environment Details
- Date (UTC): <fill>
- Replit workspace type: <fill>  (e.g., “Default Nix Python”)
- Python version: <paste output of `python3 --version`>
- Platform: <paste `python3 -c "import platform; print(platform.platform())"`>
- Repo commit (short SHA): <fill>

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
- out/sf_packet.preview.json (SHA256): <fill>
- examples/expected_outputs/sf_packet.example.json (SHA256): <fill, optional>

Result
- Status: PASS
- Notes: <any relevant observations; keep concise>
