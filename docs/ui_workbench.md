# Orchestrate OS — Workbench (Review States + Triage)

> **Operator** = a human user (Analyst/Verifier/Admin) performing non-gated actions.

Audience
- Non‑technical Analysts and Verifiers working with artifacts only (offline‑first).

Purpose
- The Workbench is your primary triage screen. Load artifacts, inspect Review States, open a record, review issues/actions, and (optionally) open Patch Studio. All interactions are offline‑first; no network calls or external execution required.

What you see (panels)
- Review States Panel: deterministic tables (To Do, Needs Review, Flagged, Blocked, Finalized)
- Record Context Panel (drawer): identity keys (contract_key → file_url → file_name), fields, issues, field actions
- PDF Viewer: local PDF with deterministic highlights and navigation
- Evidence Strip: pasted gate status chips (Base/Validation/Conflicts/Smoke)
- Toolbar: Data Source, Ruleset, Compare, Run (all in modals; offline‑first)

Buttons & actions (deterministic)
- Data Source (modal): add or switch data source, load Preview Packet and Reference Expected. [screenshot: Data Source]
- Ruleset (modal): select Truth Config (base) and Proposed Changes (patch). [screenshot: Ruleset]
- Compare (modal): normalized side‑by‑side Preview vs Expected (no diff engine beyond normalization). [screenshot: Compare]
- Run (modal): copy commands for validate/preview/smoke (offline reference; UI does not execute external processes). [screenshot: Run Modal]
- Build Patch: opens Patch Studio from Workbench for the current selection. [screenshot: Build Patch]
- Submit Patch Request: the official in‑app submission path. Submits the patch draft with evidence pack and preflight results into the review pipeline (Analyst → Verifier → Admin). Gated by Evidence Pack completeness and Preflight checks.

Review States (entry point)
- Sorting (always): severity (blocking > warning > info), then contract_key, file_url, file_name (asc; nulls last)
- To Do: READY/NEEDS_REVIEW, not Blocked/Finalized
- Needs Review: requires verifier confirmation
- Flagged: warning or explicitly flagged
- Blocked: blocking issues detected (e.g., join failure)
- Finalized: verifier/admin‑approved (no further action)

What it produces
- Workbench feeds Patch Studio context (record + field/issue links) and supports in‑app patch submission.

Where it goes
- When clicking Build Patch, Patch Studio receives current record context (identity keys, sheet/field, issue references) for drafting.
- When clicking Submit Patch Request, the patch enters the review pipeline with its evidence pack and preflight results.

Offline‑first vs Submit
- Offline‑first: you can copy JSON for rules/patch/PR summary at any time; no network required for drafting.
- Submit Patch Request: the official in‑app submission path. The UI validates Evidence Pack completeness and Preflight gates before allowing submission into the Analyst → Verifier → Admin pipeline.

Determinism
- Identity keys drive all sorting and links; nulls are explicit and sort last.
- Editor/LSP diagnostics are non‑authoritative; Preview Packet + smoke are the arbiter.

Troubleshooting
- Empty Review States: ensure Preview Packet loaded.
- Missing highlights: confirm local PDF selection; highlights rely on deterministic mapping from Preview Packet.
