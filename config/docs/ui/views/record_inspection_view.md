# Record Inspection (stub)

This file is a maintenance stub retained to avoid broken links.

**Record Inspection** is the canonical UI label for this surface. The internal token `single_row_review` (legacy/internal token) is retained in routes, specs, and audit logs.

- Primary contract: docs/ui/views/single_row_review_view.md
- Purpose: authoritative, per-record inspection with evidence and patch authoring by Analysts; Verifier/Admin read-only in this view.
- Review States: To Do, Needs Review, Flagged, Blocked, Finalized (badges are rendered; no transitions here).
- Actions:
  - Save Patch Draft
  - Submit Patch Request (submits in-app to Verifier Review; sets status to Submitted)
- No gates owned; gating decisions occur in Verifier Review and Admin Approval.

Please update any remaining references to this path to point to:
docs/ui/views/single_row_review_view.md
