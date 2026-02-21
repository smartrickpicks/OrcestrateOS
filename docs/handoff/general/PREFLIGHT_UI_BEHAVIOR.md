# Preflight UI Behavior

## Panel Location
The Preflight panel is accessible via a "Preflight" tab button in the floating grid controls bar (alongside Suggestions).

## Admin-Only Sandbox Behavior
- Non-admin users: Preflight tab is hidden by default
- If shown, Run Preflight, Accept Risk, and Escalate OCR controls are hidden/disabled
- Inline note displayed: "Admin-only sandbox."
- Non-admin users cannot trigger persistence side-effects from preflight actions

## Gate Display
- GREEN badge: Green background, "All checks passed. Ready to submit."
- YELLOW badge: Amber background, shows Accept Risk and Escalate OCR buttons
- RED badge: Red background, shows only Escalate to OCR button

## Metrics Display
Shows: Total Pages, Searchable, Scanned, Mixed, Avg Chars/Page

## Reason Codes
Human-readable translations of engine reason codes displayed as bullet points.

## Submit Enforcement
`validateSubmissionGates()` checks the canonical `_pfGateState` object:
- GREEN: allow submission
- YELLOW: block until Accept Risk or Escalate OCR (admin-only actions)
- RED: block until Escalate OCR (admin-only action)

**Admin-only bypass:** `srrCheckSyncPreflightGate()` returns `[]` (no gaps) when `_pfGateState.adminOnly` is true, ensuring non-admin users are never blocked by preflight gates they cannot interact with.
