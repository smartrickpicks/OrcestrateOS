# Orchestrate OS — Patch Studio (Overlay Authoring)

Audience
- Non‑technical Analysts preparing Proposed Changes; Verifiers inspecting drafts.

Purpose
- Author structured rule patches inside a contextual overlay. Patch Studio can be opened from Workbench (recommended) or from navigation.

Panels
- Intent (plain English): WHEN / THEN / BECAUSE
- Mapping (schema): rule_id, when{sheet, field, operator, value?}, then[action, sheet, field, severity, proposed_value?]
- Patch Draft: changes[] with one or more add_rule entries

Buttons & actions
- Copy Rule JSON: copies the rule mapping block (single rule)
- Copy Patch JSON: copies the patch draft (base_version required)
- Submit Patch Request: submits the patch draft for Verifier review via the in-app governance workflow
- Close Overlay: returns to Workbench without writing

What it produces
- Proposed Changes (patch draft JSON) with sorted keys, ready for review. Example path suggestion: config/config_pack.vX.Y.Z.patch.json

Where it goes
- Submit Patch Request routes the draft into the Verifier Review queue. Alternatively, Copy Patch JSON allows pasting into an external editor for Git-based workflows.

Submit workflow
- Analysts submit patch drafts in-app via Submit Patch Request. Copy to clipboard remains available for external Git/PR workflows.

Determinism safeguards
- Allowed operators: IN, EQ, NEQ, CONTAINS, EXISTS, NOT_EXISTS
- Allowed actions: REQUIRE_PRESENT, REQUIRE_BLANK, SET_VALUE
- Severity order influences gates and sorting; choose the lowest severity that protects quality.

Verifier notes
- Verifiers can inspect the overlay, request changes, or accept at Preflight after evidence is reviewed.

[screenshot: Patch Studio overlay]
