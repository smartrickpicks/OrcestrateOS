# Orchestrate OS — Preflight (Evidence Gate)

Audience
- Reviewers (primary), Analysts (to prepare evidence).

Purpose
- Gate PR readiness using paste‑in evidence only. No execution; no file writes. Preflight must show all gates satisfied: Base Version Check, Validation Report, Conflict Check, Smoke Evidence.

Inputs (paste‑in)
- Base Version: base.version string or JSON header snippet
- Patch Base Version: patch.base_version extracted from patch JSON
- Validation Evidence: validator stdout/JSON (status ok/error, changes_count, conflicts)
- Smoke Evidence: baseline (required) and edge (if applicable) logs; optional SHA256 hashes

Buttons & actions
- Parse: attempts to extract key fields from pasted text; otherwise mark manual
- Generate PR Summary: deterministic text including Evidence section
- Copy PR Summary: copy‑only; paste into PR description
- Reset Evidence: clears evidence only; does not modify drafts

What it produces
- Deterministic PR summary text containing Base/Patch versions, validation status, conflicts count, smoke baseline/edge pass/fail, and optional SHA256s.

Where it goes
- Paste into PR description or ticketing system as governance evidence.

Determinism & authority
- Smoke Evidence is the arbiter; editor diagnostics are non‑authoritative.
- Sorting rules: severity then identity keys; nulls last.

[screenshot: Preflight with chips]
