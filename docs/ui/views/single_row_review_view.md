# Single Row Review View — Authoritative, Per-Record Inspection

Contract: This document defines the record-level inspection surface. It supports Evidence Pack authoring and Patch Draft creation by Analysts while remaining read-only for Verifier/Admin with respect to gates and Review State transitions.

> **UI Label vs Canonical Name**
> - **UI Label (user-facing):** Record Inspection
> - **Canonical Name (specs/audit/routes):** Single Row Review
>
> The user-facing label "Record Inspection" appears in the UI header and navigation. All internal tokens, routes, specs, and audit logs retain the canonical name `single_row_review`.

## Recent Changes (v1.5.0)

- **Field Inspector State Model**: Updated to 6-state model (todo, verified, modified, submitted, rfi, blocked)
- **RFI Workflow**: Fields stay in To Do queue until "Send RFI" clicked (rfi_pending intermediate state)
- **Patch Editor Reset**: Form automatically clears after payload submission to prevent carry-over
- **Verifier Payload Wiring**: RFI, Correction, and Blacklist submissions create payloads for Verifier queue
- **State Badge Colors**: Green (verified), Blue (modified/submitted), Orange (rfi), Red (blocked)

## Purpose
- Provide authoritative, per-record context: baseline values, deltas, flags, evidence, and audit trail.
- Enable Analysts to author Evidence Packs and create Patch Drafts with explicit rationale and evidence anchoring.
- Maintain strict separation of duties: no direct Review State transitions from this view.

## Roles & Permissions
- Analyst:
  - May edit the Evidence Pack panel to create or update Patch Drafts.
  - May save a Patch Draft and submit as Patch Request for verification; this emits PATCH_DRAFTED and/or PATCH_SUBMITTED and REVIEW_REQUESTED audit events.
  - May add or clear flags with rationale (FLAG_ADDED / FLAG_CLEARED).
- Verifier/Admin:
  - Read-only in this view (inspect baseline, deltas, evidence, and audit log).
  - Gate decisions (STATE_MARKED) occur only in their dedicated governed views (verifier_review_view, admin_approval_view).

## Layout (Three-Panel)

### Top Bar
- Back to Grid button
- Record identity (contract_key or record_id)
- Review State badge (read-only display)
- Open Audit Log button (read-only link)

### Left Panel: Field Inspector as Mini-Queue (v1.5.0)

The Field Inspector functions as a **mini-queue** where each field has a discrete state and can be actioned independently. The analyst processes fields until all are resolved.

**Layout:**
- Search input (filters by field name or value, case-insensitive)
- Filter chips: All / Changed / Unchanged
- Field Cards with action buttons and state badges

**Field States (6-State Model):**

| State | Description | Color | Badge Label | Queue Behavior |
|-------|-------------|-------|-------------|----------------|
| todo | Field not yet reviewed | Gray | (none) | Stays in To Do |
| verified | Field confirmed correct | Green | Verified | Removed from To Do |
| modified | Field value edited, not yet submitted | Blue | Modified | Stays in To Do |
| submitted | Patch submitted to verifier | Blue | Patch Submitted | Removed from To Do |
| rfi_pending | RFI drafted but not sent | Orange | RFI (pending) | Stays in To Do |
| rfi | RFI sent to verifier | Orange | RFI | Stays in All (visible) |
| blocked | Blacklist flag submitted | Red | Blocked | Removed from To Do |

**Field Actions:**
Each field card exposes action buttons based on current state:

| Action | Icon | Result | Auto Patch Type |
|--------|------|--------|-----------------|
| Verify | ✓ (green) | Sets state to verified, removes from To Do | (none — no patch) |
| Blacklist Flag | 🚫 (red) | Sets state to blocked, auto-sets Patch Type | Blacklist Flag |
| RFI | ? (orange) | Sets state to rfi_pending, opens RFI input | RFI |
| Modify (edit) | ✏️ (blue) | Enables inline edit, sets state to modified | Correction |

**RFI Request Box (v1.5.0):**
When RFI action is clicked, the Patch Editor displays:
- Field name being questioned (read-only)
- Current field value (read-only)
- Justification textarea (acts as the RFI question)

**Field Ordering Rule (canonical):**
- Primary: Schema order (deterministic, from `SRR_SCHEMA_ORDER`)
- Fallback: Alphabetical for unknown fields not in schema

**Inline Editing Behavior:**
- Click Patch action (or value display) to enter edit mode
- On blur/Enter: Commit edit, lock field, set state to PATCHED
- Locked fields cannot be edited inline (use Patch Editor to modify)

**Filters:**
- All: Show all fields
- TODO: Show fields not yet reviewed
- VERIFIED: Show fields marked as correct
- RFI: Show fields with pending questions
- PATCHED: Show fields with value changes

### Center Panel: Document Viewer (v1.4.17)
- **PDF Rendering**: Displays PDFs via browser's native PDF viewer (iframe-based)
- **PDF Proxy**: Network PDFs are fetched via proxy to avoid CORS issues
  - Primary: Supabase Edge Function
  - Fallback: FastAPI on port 8000
- **Offline Cache**: Successfully fetched PDFs are cached in IndexedDB

### Right Panel: Patch Editor + Evidence Pack (v1.4.19)

**Patch Type Selector (Read-Only):**
Patch Type is **auto-determined** by the field action and displayed as a read-only indicator:

| Field Action | Auto Patch Type |
|--------------|-----------------|
| Patch (edit) | Correction |
| Blacklist Flag | Blacklist Flag |
| RFI | RFI |

The analyst cannot manually change the Patch Type; it reflects the semantic intent of the action taken. This ensures deterministic audit trails and consistent Evidence Pack requirements.

**Changed Fields Section:**
- Shows count of committed changes (PATCHED fields)
- Per-field blocks with:
  - Field label + remove button
  - Old value (locked, subdued, strikethrough)
  - New value (editable input, prominent green border)
- Editing new value syncs to Field Inspector display

**Override Toggle (Correction only):**
- Appears when Observation = "Override Needed" OR Expected = "Allow Override"
- When enabled: Repro block hidden, Override badge shown in header
- Purpose: Skip repro requirement for documented exceptions

## Auto Patch Type Semantics (v1.4.20)

### Correction (via Patch action)
- Triggered by: Editing a field value
- Evidence Pack: Full (Observation + Expected + Justification + Repro)
- Requires: At least one field change

### Blacklist Flag (via Blacklist Flag action)
- Triggered by: Clicking Blacklist Flag button on a field
- Evidence Pack: Justification only
- Blacklist Subject: Read-only, auto-derived from selected field name and value
  - Format: `{field_label}: {current_value}`
  - Example: "Artist Name: John Doe"
- Blacklist Category: Dropdown selector with options:
  - Duplicate Entry
  - Invalid Format
  - Prohibited Value
  - Data Quality Issue
  - Other (with custom reason)
- Field change: Optional (flagging does not require value edit)

### RFI (via RFI action)
- Triggered by: Clicking RFI button on a field
- Evidence Pack: Justification only
- RFI behavior: The Justification textarea **is** the question
  - Placeholder: "What is your question about this field?"
  - The entered text becomes the RFI question body
- RFI Target: Optional routing field (Team Lead, Legal, Data Steward, etc.)
- Field change: Optional (RFI does not require value edit)

## Evidence Pack (v1.4.19)

Simplified structure with dropdowns only (no free-text observation/expected notes):

### Observation (WHEN) — Correction only
Dropdown options:
- Incorrect Value
- Missing Value
- Formatting Issue
- Duplicate Entry
- Inconsistent Data
- Override Needed

### Expected (THEN) — Correction only
Dropdown options:
- Use Correct Value
- Populate Empty Field
- Standardize Format
- Remove Duplicate
- Align with Source Document
- Allow Override

### Justification (BECAUSE) — All patch types
Single narrative textarea explaining the change/flag/question.
- For Correction: Explains why the change is correct
- For Blacklist Flag: Explains why the value should be blacklisted
- For RFI: **Is the question itself** (acts as the RFI body)

### Repro Method — Correction only (when not Override)
Dropdown options:
- Breaks Salesforce Rule
- Breaks QA Gate
- Resolver Mismatch
- Doc Evidence Mismatch (requires file attachment)

## Patch Type Behavior

| Type | Required Fields | Optional |
|------|-----------------|----------|
| Correction | Observation + Expected + Justification + Repro (unless Override) + Field changes | Override |
| Blacklist Flag | Justification (min 10 chars) + Blacklist Category | Field changes |
| RFI | Justification (min 10 chars) | RFI Target, Field changes |

## Validation Rules

### Correction
- Observation type: Required
- Expected type: Required
- At least one field change: Required
- Repro method: Required (unless Override enabled)
- File attachment: Required if Repro = "Doc Evidence Mismatch"

### Blacklist Flag
- Justification: Required (minimum 10 characters)
- Blacklist Category: Required
- Field changes: Optional

### RFI
- Justification: Required (minimum 10 characters) — this is the question
- RFI Target: Optional
- Field changes: Optional

## Patch Editor Reset Behavior (v1.5.0)

After any successful submission (RFI, Correction, or Blacklist), the Patch Editor automatically resets to prevent data carry-over between records:

**Cleared on Submit:**
- Comment/Justification input
- Patch type selection (reset to Correction default)
- Old/New value displays
- RFI field reference (srrState.rfiField)
- Blacklist subject display
- Proposed changes and locked fields
- Override toggle state
- Evidence Pack dropdowns (Observation, Expected, Repro)

**Preserved:**
- Verifier payloads in localStorage (persist independently)
- Field states on current record (verified, submitted, etc.)

## Unsaved Changes Guard (v1.4.20)

If the user attempts to navigate away (Back to Grid) with **unresolved PATCHED or RFI fields**, a modal appears:

**Trigger Conditions:**
- Any field in PATCHED state (uncommitted edits)
- Any field in RFI state (unsubmitted question)
- VERIFIED fields do NOT trigger the guard (they are resolved)

**Guard Modal:**

| Button | Action |
|--------|--------|
| Cancel | Close modal, stay on Single Row Review |
| Discard Changes | Clear all PATCHED and RFI states, navigate to Grid |
| Submit Patch Request | Run `submit_patch_request` for pending items, then navigate to Grid |

**Modal Message:**
> "You have {N} unresolved fields (PATCHED or RFI). Do you want to submit a Patch Request before leaving?"

## Audit Integration
- Opening this view emits a VIEWED event (context: "record").
- All Evidence Pack authoring emits the appropriate PATCH_* events.
- Field state changes emit FIELD_STATE_CHANGED events with {field, from_state, to_state}.
- No STATE_MARKED events originate from this view.

## Navigation
- From All Data Grid → Single Row Review (this view).
- From this view:
  - Open Audit Log detail (read-only overlay or linked panel).
  - Navigate to governed gating views via explicit links.
  - Back to Grid (guarded if unresolved PATCHED/RFI fields exist).

## Read-Only & Gate Separation
- No approve, promote, or finalize actions are available in this view.
- Review State transitions are owned exclusively by governed gate views.

## Acceptance Tests (v1.4.20)

| ID | Test | Expected |
|----|------|----------|
| SRR-MQ-01 | Field Inspector shows filter chips for TODO/VERIFIED/RFI/PATCHED | Four filter chips visible |
| SRR-MQ-02 | Verify action sets field to VERIFIED state | Green check chip appears |
| SRR-MQ-03 | Blacklist Flag action auto-sets Patch Type to "Blacklist Flag" | Patch Type read-only, shows Blacklist Flag |
| SRR-MQ-04 | RFI action auto-sets Patch Type to "RFI" | Patch Type read-only, shows RFI |
| SRR-MQ-05 | Patch (edit) action auto-sets Patch Type to "Correction" | Patch Type read-only, shows Correction |
| SRR-MQ-06 | Blacklist Subject derived from field name + value | Read-only display shows "Field: Value" |
| SRR-MQ-07 | RFI Justification acts as question body | Placeholder indicates "What is your question..." |
| SRR-MQ-08 | Guard modal appears with unresolved PATCHED/RFI fields | Modal shows count and options |
| SRR-MQ-09 | Guard modal does NOT appear with only VERIFIED fields | Navigation proceeds without modal |
| SRR-PT-01 | Old/New values visually distinct | Old: subdued, strikethrough; New: prominent green border |
| SRR-PT-02 | Observation/Expected are dropdowns only | No textarea for observation/expected notes |
| SRR-PT-03 | Patch Type changes visible form sections | Blacklist/RFI hide Observation/Expected/Repro |
| SRR-PT-04 | Repro controls appear only when required | Hidden for Blacklist/RFI or when Override enabled |
| SRR-PT-05 | Override badge appears and suppresses repro | Badge visible in header, repro block hidden |

## References

- [Field Inspector Patch Flow](single_row_review_field_inspector_patch_flow.md)
- [Human-Agent-Workflow-V1.json](../../specs/Human-Agent-Workflow-V1.json) — single_row_review node
- [Gate View Mapping](../gate_view_mapping.md)
