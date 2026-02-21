# Orchestrate OS — Preflight (Evidence Gate)

Audience
- Verifiers (primary), Analysts (to prepare evidence).

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

## Pre-Flight Triage (V2.3)

Pre-Flight is the first triage bucket in the Analyst view. It surfaces blockers that must be resolved before semantic review can proceed.

### Blocker Types
| Type | Description | Default Severity |
|------|-------------|-----------------|
| UNKNOWN_COLUMN | Column not in canonical schema | Computed: >0 non-empty = warning, >3 non-empty = blocker |
| OCR_UNREADABLE | Document text extraction failed | blocker |
| LOW_CONFIDENCE | Extraction confidence below threshold | warning |
| MOJIBAKE | Character encoding corruption detected | blocker |

### Unknown Column Severity (V2.3 Locked)
Severity for unknown columns is computed from the rollup, not hardcoded:
- `non_empty > 0` → `severity: 'warning'`
- `non_empty > 3` → `severity: 'blocker'`

Thresholds are constants: `_UNKNOWN_WARN_THRESHOLD = 0`, `_UNKNOWN_BLOCKER_THRESHOLD = 3`.

### One-Click Patch Creation
Each Pre-Flight blocker with `can_create_patch: true` offers a "Create Patch from Blocker" action that generates a governed patch routed through the standard lifecycle.

[screenshot: Preflight with chips]
