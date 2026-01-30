# Orchestrate OS — Patch Studio (Overlay Authoring)

Audience
- Non‑technical Analysts preparing Proposed Changes; Reviewers inspecting drafts.

Purpose
- Create copy‑only JSON for rule patches inside a contextual overlay (no execution, no writes). Patch Studio can be opened from Workbench (recommended) or from navigation.

Panels
- Intent (plain English): WHEN / THEN / BECAUSE
- Mapping (schema): rule_id, when{sheet, field, operator, value?}, then[action, sheet, field, severity, proposed_value?]
- Patch Draft: changes[] with one or more add_rule entries (copy‑only)

Buttons & actions
- Copy Rule JSON: copies the rule mapping block (single rule)
- Copy Patch JSON: copies the patch draft (base_version required)
- Close Overlay: returns to Workbench without writing

What it produces
- Proposed Changes (patch draft JSON) with sorted keys, ready for PR. Example path suggestion: config/config_pack.vX.Y.Z.patch.json

Where it goes
- Paste into a file in your editor (outside the viewer) and commit via Git. Or include in a PR branch with smoke evidence.

Copy‑only vs Submit
- Patch Studio never saves; copy to clipboard, then paste into your repo editor.

Determinism safeguards
- Allowed operators: IN, EQ, NEQ, CONTAINS, EXISTS, NOT_EXISTS
- Allowed actions: REQUIRE_PRESENT, REQUIRE_BLANK, SET_VALUE
- Severity order influences gates and sorting; choose the lowest severity that protects quality.

Reviewer notes
- Reviewers can inspect the overlay, request changes, or accept at Preflight after evidence is pasted.

[screenshot: Patch Studio overlay]
