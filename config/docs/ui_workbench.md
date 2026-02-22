# Orchestrate OS — Workbench (Review States + Triage)

> **Operator** = a human user (Analyst/Verifier/Admin) performing non-gated actions.

Audience
- Non-technical Analysts and Verifiers working with artifacts only (offline-first).

Purpose
- The Workbench is your primary triage screen. Load artifacts, inspect Review States, open a record, review issues/actions, and (optionally) open Patch Studio. All interactions are offline-first; no network calls or external execution required.

What you see (panels)
- Review States Panel: deterministic tables (To Do, Needs Review, Flagged, Blocked, Finalized)
- Record Context Panel (drawer): identity keys (contract_key -> file_url -> file_name), fields, issues, field actions
- PDF Viewer: local PDF with deterministic highlights and navigation
- Evidence Strip: pasted gate status chips (Base/Validation/Conflicts/Smoke)
- Toolbar: Data Source, Ruleset, Compare, Run (all in modals; offline-first)

Buttons & actions (deterministic)
- Data Source (modal): add or switch data source, load Preview Packet and Reference Expected.
- Ruleset (modal): select Truth Config (base) and Proposed Changes (patch).
- Compare (modal): normalized side-by-side Preview vs Expected (no diff engine beyond normalization).
- Run (modal): copy commands for validate/preview/smoke (offline reference; UI does not execute external processes).
- Build Patch: opens Patch Studio from Workbench for the current selection.
- Submit Patch Request: the official in-app submission path. Validates evidence pack, replay contract, and preflight gates. Creates a patch request with status `Submitted` routed to the Verifier review queue. **Submit is not approval** — it only creates a reviewable item.

Review States (entry point)
- Sorting (always): severity (blocking > warning > info), then contract_key, file_url, file_name (asc; nulls last)
- To Do: READY/NEEDS_REVIEW, not Blocked/Finalized
- Needs Review: requires verifier confirmation
- Flagged: warning or explicitly flagged
- Blocked: blocking issues detected (e.g., join failure)
- Finalized: verifier/admin-approved (no further action)

What it produces
- Workbench feeds Patch Studio context (record + field/issue links) and supports in-app patch submission.

Where it goes
- When clicking Build Patch, Patch Studio receives current record context (identity keys, contract section/field, issue references) for drafting.
- When clicking Submit Patch Request, the patch enters the review pipeline with its evidence pack, replay contract, and preflight results.

Offline-first vs Submit
- Offline-first: you can copy JSON for rules/patch/PR summary at any time; no network required for drafting.
- Submit Patch Request: the official in-app submission path. The UI validates Evidence Pack completeness, Replay Contract (per patch type), and Preflight gates before allowing submission into the Analyst -> Verifier -> Admin pipeline.

Role restrictions
- **Analyst**: Can submit patches. Cannot approve or promote.
- **Verifier**: Can review and approve (with checklist). Cannot self-approve. Cannot perform final promotion.
- **Admin**: Can perform final approval and promotion. Cannot self-approve.
- Unauthorized actions are hidden from the UI, not disabled.

Determinism
- Identity keys drive all sorting and links; nulls are explicit and sort last.
- Editor/LSP diagnostics are non-authoritative; Preview Packet + smoke are the arbiter.

Troubleshooting
- Empty Review States: ensure Preview Packet loaded.
- Missing highlights: confirm local PDF selection; highlights rely on deterministic mapping from Preview Packet.
