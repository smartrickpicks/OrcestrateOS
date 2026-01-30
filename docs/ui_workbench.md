# Orchestrate OS — Workbench (Queues + Triage)

Audience
- Non‑technical Analysts and Reviewers working with artifacts only (offline‑first).

Purpose
- The Workbench is your primary triage screen. Load artifacts, inspect queues, open a record, review issues/actions, and (optionally) open Patch Studio. All interactions are copy‑only; no network, no execution, no file writes.

What you see (panels)
- Queues Panel: deterministic tables (To Do, Needs Review, Flagged, Blocked, Finalized)
- Record Context Panel (drawer): identity keys (contract_key → file_url → file_name), fields, issues, field actions
- PDF Viewer: local PDF with deterministic highlights and navigation
- Evidence Strip: pasted gate status chips (Base/Validation/Conflicts/Smoke)
- Toolbar: Load Data, Ruleset, Compare, Run (all in modals; copy‑only)

Buttons & actions (deterministic)
- Load Data (modal): choose Preview Packet (local JSON) and Reference Expected (local JSON). [screenshot: Load Data]
- Ruleset (modal): select Truth Config (base) and Proposed Changes (patch). [screenshot: Ruleset]
- Compare (modal): normalized side‑by‑side Preview vs Expected (no diff engine beyond normalization). [screenshot: Compare]
- Run (modal): copy commands for validate/preview/smoke (UI never executes). [screenshot: Run Modal]
- Build Patch: opens Patch Studio from Workbench for the current selection. [screenshot: Build Patch]

Queues (entry point)
- Sorting (always): severity (blocking > warning > info), then contract_key, file_url, file_name (asc; nulls last)
- To Do: READY/NEEDS_REVIEW, not Blocked/Finalized
- Needs Review: requires reviewer confirmation
- Flagged: warning or explicitly flagged
- Blocked: blocking issues detected (e.g., join failure)
- Finalized: reviewer‑approved (no further action)

What it produces
- Workbench itself does not produce files. It feeds Patch Studio context (record + field/issue links).

Where it goes
- When clicking Build Patch, Patch Studio receives current record context (identity keys, sheet/field, issue references) for copy‑only draft.

Copy‑only vs Submit
- Copy‑only: you will copy JSON for rules/patch/PR summary; the UI never writes or submits.
- Submit: performed later via PR, referencing copied artifacts and pasted evidence.

Determinism
- Identity keys drive all sorting and links; nulls are explicit and sort last.
- Editor/LSP diagnostics are non‑authoritative; Preview Packet + smoke are the arbiter.

Troubleshooting
- Empty queues: ensure Preview Packet loaded.
- Missing highlights: confirm local PDF selection; highlights rely on deterministic mapping from Preview Packet.
