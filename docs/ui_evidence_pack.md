# Orchestrate OS — Evidence Pack (Reviewer Bundle)

Audience
- Reviewers and Admin preparing a complete governance bundle for a PR.

Purpose
- Assemble a copy‑only set of artifacts for review and audit. No network, no execution.

What to include
- Preview Packet (out/sf_packet.preview.json)
- Reference Expected (examples/expected_outputs/...) — baseline and edge
- Truth Config header (version) and Proposed Changes (patch draft)
- Validation Evidence (validator stdout/JSON)
- Smoke Evidence (logs; baseline required, edge if applicable; optional SHA256s)
- Optional: PDF anchors (coordinates, page refs) and identity keys

How to assemble (suggested structure)
- evidence/
  - preview/preview.json
  - expected/baseline.json
  - expected/edge.json
  - validation/report.txt
  - smoke/baseline.txt
  - smoke/edge.txt (optional)
  - patch/patch.json
  - notes/identity_keys.txt (contract_key/file_url/file_name)

Copy‑only vs Submit
- Evidence Pack is gathered and attached to PR as files or pasted snippets. Submit remains a PR action outside the viewer.

Determinism
- Normalize JSON keys when comparing; arrays follow stable order by identity keys.

[screenshot: Evidence Pack checklist]
