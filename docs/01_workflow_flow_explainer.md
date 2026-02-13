# 01 — Workflow Flow Explainer: How a Contract Moves Through Orchestrate OS

## Who This Is For

Anyone who needs to understand the end-to-end journey of contract data through Orchestrate OS — from the moment a spreadsheet is loaded to the moment corrected data is exported and archived.

## The Big Picture

A contract workbook enters the system, gets scanned for problems, goes through human review and correction, passes through approval gates, and exits as governed, auditable data. Every step is tracked. Every change requires evidence. Every approval requires the right person.

## Step-by-Step Flow

### 1. Data Enters the System (Discovery Plane)

**What happens:** An Analyst loads a contract workbook — either by uploading an Excel/CSV file directly, or by importing it from Google Drive through the Data Source panel.

**Behind the scenes:**
- The workbook parser reads all sheets (Accounts, Catalog, Contact, Finance, Opportunity, Schedule, Schedule Catalog)
- Column names are mapped to canonical names using 479 alias entries
- Header-echo rows (duplicate header rows buried in data) are detected and removed
- The workbook is cached in the browser's IndexedDB for session persistence
- If imported from Drive, the import provenance is recorded in the database with a full audit trail

**What the Analyst sees:** The Triage dashboard populates with the loaded data. Progress bar shows To Do / Review / Done counts.

### 2. Pre-Flight Checks Fire (Discovery → Control Transition)

**What happens:** Automated quality gates run immediately after the workbook loads. These catch problems that would block downstream work.

**Checks that run:**
- **Unknown Columns** — Are there column headers the system doesn't recognize? If so, they're flagged for the Analyst to map or investigate.
- **OCR Quality** — If PDFs are attached, are they searchable? Non-searchable or mojibake content gets flagged.
- **Duplicate Accounts** — Are there account pairs that look like duplicates? The system uses deterministic field comparison to detect them.
- **Incomplete Addresses** — Are address fields missing city, state, or zip? The ADDRESS_INCOMPLETE_CANDIDATE matching system finds candidates and routes warnings or blockers.

**What the Analyst sees:** Pre-flight results appear in the Triage view. Blockers must be resolved before the contract can advance. Warnings are informational but tracked.

### 3. Signal Engine Scans (Control Room)

**What happens:** The Signal Engine runs semantic rules across every record in the dataset. Rules come from `field_meta.json` and `qa_flags.json` in the rules bundle.

**What it produces:**
- `MISSING_REQUIRED` signals — a required field is empty
- `OCR_UNREADABLE` signals — a field value looks like garbled OCR output
- Other validation signals based on field type, format, and business rules

**What the Analyst sees:** Signal counts appear in the Triage header. Records with signals flow into the Analyst's triage queue. The grid highlights affected cells — red for blockers, orange for warnings.

### 4. Contract Index Builds (Control Room)

**What happens:** The Contract Index Engine builds a hierarchy from the loaded data:

```
Batch
  └── Contract (derived from file URL/name)
        └── Document (individual files)
              └── Section (sheet within the workbook)
                    └── Row (individual records)
```

**What the Analyst sees:** The Contract Summary in the Triage view shows contracts with their health scores (0-100), categorized as Critical, At Risk, Watch, or Healthy.

### 5. Analyst Triage (Control Room — Hot Route)

**What happens:** The Analyst works through their queue. For each flagged record, they:

1. **Inspect** — Open the Record Inspector to see field values, signals, and related records
2. **Check evidence** — Open the PDF Viewer to find the source document and locate the relevant clause or data point
3. **Correct** — Edit cell values directly in the grid (Grid Mode) or draft a formal patch in Patch Studio
4. **Attach evidence** — Build an Evidence Pack with observations, expected values, justification, and PDF anchor references
5. **Submit** — Submit the patch for verification

**Drafts are private.** While an Analyst is drafting a patch, only they can see it. Like a Discord ephemeral message, the draft is invisible to Verifiers and Admins until submitted. The Analyst can revise freely without pressure.

**RFIs work both ways.** If an Analyst encounters something they can't resolve alone, they can submit an RFI (Request for Information) with a justification explaining why they need help. RFIs are persisted to the database with full audit trail.

### 6. Verifier Review (Control Room — Cold Route)

**What happens:** When an Analyst submits a patch, the system notifies the Verifier. The Verifier:

1. **Reviews** the proposed corrections against the source evidence
2. **Tests** each correction — does the new value match what the PDF actually says?
3. **Decides:**
   - **Approve** — The corrections are accurate. Patch advances toward promotion.
   - **Reject** — The corrections are wrong. Patch returns to the Analyst with feedback.
   - **RFI** — The Verifier needs clarification. An RFI is raised, and the Analyst is notified.

**Retry policy:** If a patch is rejected or an RFI is raised, the system follows a hot-route retry policy: retry → retry → escalate to cold route. This means the Analyst gets two chances to revise before the issue is escalated for broader review. No failure goes unrecorded — every retry attempt is logged in the audit timeline.

**Gate enforced:** The system prevents self-approval. An Analyst cannot verify their own patch. This is server-enforced, not just a UI rule.

### 7. Admin Promotion (Control Room — Cold Route)

**What happens:** Once a Verifier approves a patch, the Admin is notified that promotion is unlocked. The Admin:

1. **Reviews** the approved patch and its evidence trail
2. **Promotes** the correction to canonical truth — this is the final decision
3. The contract status advances to `ADMIN_FINAL`

**Gate enforced:** Only Admins can promote. The 22-transition matrix on the server validates every status change.

### 8. Export and Delivery (Execution Plane)

**What happens:** With corrections approved and promoted, the data is ready to leave the system.

**Three export options:**
- **Export** — Downloads a clean Excel file with just the data sheets and edits. No audit trail attached. This is for the Analyst who just needs the corrected spreadsheet.
- **Export Full** — Downloads the complete workbook with all audit sheets: change log, RFIs & Analyst Notes, signals summary, metadata, and audit log. This is the full evidence package.
- **Save to Drive** — Uploads the full workbook (same as Export Full) directly to Google Drive. This is the handoff mechanism — a Verifier or stakeholder can pick up this file from Drive and see exactly what changed and why.

**Naming convention:** All exports follow the pattern `{dataset}__{STATUS}__{yyyy-mm-dd_HH-mm}__{workspace}.xlsx`. The status reflects the current workflow stage: `IN_PROGRESS_ANALYST`, `ANALYST_DONE`, `VERIFIER_DONE`, `ADMIN_FINAL`, or `REJECTED`.

**Cell styling:** Exported files carry visual indicators — red fills for blocker cells, orange for RFI cells, green for verified cells.

### 9. Archive (Execution Plane)

**What happens:** The contract's audit trail is sealed. All events, artifacts, evidence packs, and decision records are preserved as immutable history. The append-only audit event log ensures nothing can be retroactively altered.

## Lifecycle at a Glance

```
LOADED → PREFLIGHT_COMPLETE → SYSTEM_PASS_COMPLETE → SYSTEM_CHANGES_REVIEWED
  → PATCH_SUBMITTED → RFI_SUBMITTED (if needed) → VERIFIER_COMPLETE
  → ADMIN_PROMOTED → APPLIED → ARCHIVED
```

## What Makes This Different

1. **Evidence-first** — You can't just change a number. You have to prove why it should change, with a reference to the source document.
2. **No silent changes** — Every edit, every approval, every rejection is an audit event.
3. **Role separation is real** — The server enforces role gates. The UI can't bypass them.
4. **Deterministic** — Same inputs + same rules = same outputs. Always. No AI in the governance path.
5. **Contract-centric** — Everything is organized around the contract, not around individual records or fields. One contract = one channel of activity.
