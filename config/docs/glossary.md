# Glossary — Orchestrate OS

- Orchestrate OS: The offline‑first, deterministic, config‑driven governance surface for semantics.
- Control Board UI (component): The operator-facing UI surfaces (viewer/work surface) within Orchestrate OS; copy‑only, no execution.
- Preview Packet: Deterministic preview evidence produced by the harness (sf_packet JSON in code contexts).
- Truth Config: The authoritative base semantics (config_pack.base.json).
- Proposed Changes: A patch file with changes[] describing rule updates.
- Reference Expected: Expected output JSON for smoke comparison.
- Evidence Strip: UI summary of pasted Validation/Smoke/Conflicts state.
- Record Context Panel: Drawer showing the selected record’s identity keys, fields, issues, and actions.
- Identity Keys (join_triplet): contract_key → file_url → file_name; nulls last; no fabrication.
- Validation Evidence: Validator result indicating shape/conflicts status and counts.
- Smoke Evidence: Strict baseline/edge pass/fail proof of preview determinism.
- Patch Overlay: In‑place overlay to author rule/patch snippets contextual to a field/record (copy‑only export).
- Review States (To Do / Needs Review / Flagged / Blocked / Finalized): Deterministic sets driving triage and record state.
- Roles (Analyst/Verifier/Admin): Analyst drafts; Verifier verifies and approves; Admin governs configuration and policy.