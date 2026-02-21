# Orchestrate OS — Analyst UI Walkthrough (v2.53)

> A first-time user guide for Analysts. Written as a companion script for the demo walkthrough video. Replace placeholder image references with your own screenshots.

---

## Scene 1: Logging In and Landing

When you first open Orchestrate OS, you'll land on the main dashboard. The left sidebar is your command center — it's always visible and gives you quick access to everything.

**What you'll see:**
- **Progress bar** at the top of the sidebar showing To Do / Review / Done counts
- **Active Data Source** indicator showing which workbook is currently loaded
- **Mode badge** showing your current role (Analyst)
- **Navigation links** for Triage, Record Inspector, and other views
- **Your profile** at the bottom with your name, role, and a SANDBOX badge if you're in demo mode

**Key point for new users:** Your role determines what you can do. As an Analyst, you can load data, review flagged records, write corrections, attach evidence, and submit patches for review. You can't approve patches — that's the Verifier's and Admin's job.

`[IMAGE: Full sidebar with progress bar, navigation, and user profile]`

---

## Scene 2: Loading a Dataset

Before you can do anything, you need data. Click **Add Data Source** (or the upload button in the toolbar).

**Three ways to load data:**
1. **Upload a file** — Drag and drop or browse for a CSV or Excel workbook
2. **Load from Google Drive** — Connect your Drive, browse folders, and pick a workbook
3. **Use the sample dataset** — Great for learning the ropes (available in Sandbox mode)

Once loaded, the system automatically:
- Indexes all contracts and records
- Runs Pre-Flight checks (data quality, missing values, encoding issues)
- Generates semantic signals based on the rules bundle
- Populates the Triage dashboard with actionable items

**Key point:** Loading data doesn't change anything — it's read-only analysis. The original file is never modified.

`[IMAGE: Data source panel with upload/Drive/sample options]`

---

## Scene 3: The Triage Dashboard — Your Home Base

After data loads, the Triage view is where you spend most of your time. Think of it as your inbox — it shows you everything that needs attention.

**Top section — Batch Summary strip:**
- **Contracts** — How many contracts are in this workbook
- **Records** — Total data rows across all sheets
- **Completed / Needs Review / Pending** — Progress tracking
- **Updated** — When the dashboard last refreshed

**Three lanes below the summary:**

| Lane | What it catches | Example |
|------|----------------|---------|
| **Pre-Flight** | Data quality issues before semantic analysis | Missing required fields, encoding errors (Mojibake), unrecognized columns |
| **Semantic** | System-generated proposals from rules | A rule says "Term must be > 0" but the value is blank |
| **Patch Review** | Corrections you or others have drafted | Draft patches, submitted patches awaiting verifier |

**Lifecycle tracker** — A horizontal strip showing how contracts progress through 9 stages, from Loaded all the way to Applied. Each stage shows a count so you can see the overall pipeline at a glance.

**Contract Summary table** — Click the expand arrow to see every contract listed with its current stage, alert counts, and a "View in Grid" action button.

**Schema Snapshot** — Shows how well your data maps to the governed glossary. Columns Mapped %, Unknown Columns, Missing Values, and Data Quality scores.

`[IMAGE: Full Triage dashboard with all sections visible]`

---

## Scene 4: The Pre-Flight Table — Drilling Into Issues

Click on the **Pre-Flight** lane card or scroll down to the Pre-Flight section. This is a nested table — contracts are the parent rows, and individual issues are the child rows underneath.

**Parent row (contract level):**
- Contract name, compact ID, source domain
- Total issue count and severity badges (blockers in red, warnings in orange)
- Section chips showing which sheets have issues (e.g., "Accounts(3), Financials(1)")
- "View Contract" button to jump to that contract's data in the grid

**Child row (issue level):**
- Contract Section (which sheet), Reference (the business identifier), Issue description
- Severity (Blocker or Warning), Status (Open or Resolved)
- View action to open the specific record, Patch action when applicable

**Key point:** Blockers stop a contract from progressing. You need to resolve them before the contract can move to the next stage.

`[IMAGE: Pre-flight table expanded showing parent and child rows]`

---

## Scene 5: The Grid — Seeing All Your Data

Click **Record Inspector** in the sidebar (or click "View in Grid" from any contract in the Triage dashboard). This opens the data grid — a spreadsheet-like table of all your records.

**What makes this grid special:**

- **Frozen first column** — The record label (Contract: Account) stays pinned on the left as you scroll horizontally, so you always know which row you're looking at
- **Sticky headers** — Column headers stay at the top as you scroll down
- **Actions column** (left edge) — Two buttons per row:
  - **Magnifying glass** — Opens Review Mode (the detailed record drawer)
  - **Link icon** — Opens the source contract document (only shows when a file URL exists)
- **Color-coded cells** — Signals and flags show up as colored highlights on individual cells
- **Sheet tabs** at the top — Switch between different data sections (Accounts, Catalog, Contacts, etc.)

**Composite view** — When you first open the grid, it shows all sections stacked vertically (Accounts section, then Catalog, then Contacts, etc.). Each section is collapsible. You can also switch to a single-sheet view using the tabs.

`[IMAGE: Grid view showing frozen column, headers, and colored cells]`

---

## Scene 6: Evidence Viewer — Reading Source Documents

When Evidence Viewer mode is active (click the "Evidence Viewer" tab in the grid header), the layout splits into two panels:

**Left panel — Document viewer:**
- Shows the source contract PDF for the selected record
- **Reader/PDF toggle** — Switch between formatted text view (Reader) and native PDF embed
- Reader mode extracts and formats the document text for easy reading, with headings, lists, and paragraphs detected automatically
- **Mojibake detection** — Garbled text is highlighted with visual classifications (suspect or unreadable) and an OCR escalation option

**Header bar — Record context (now prominent):**
- A bold blue label shows exactly which record you're viewing: "Contract: AccountName" or similar
- This is your anchor — when you're reading the left panel and lose track of which row you're on, just glance at this label

**Right panel — Evidence Details:**
- Three collapsible sections:
  - **Linked Fields** — Text anchors connecting document passages to data fields
  - **Corrections** — Any corrections filed against this record
  - **RFIs** — Request for Information items for this record

**Selection actions:** Highlight text in the Reader view to get a quick action menu:
- Create an Evidence Mark (link text to a field)
- Create an RFI (ask the counterparty a question)
- Create a Correction (flag incorrect text)

`[IMAGE: Evidence Viewer with Reader mode, record label, and details panel]`

---

## Scene 7: Record Inspector — The Detail Drawer

Click the **magnifying glass** in the Actions column (or click a row in non-Evidence Viewer mode) to open the Record Inspector drawer on the right side.

**What's in the drawer:**
- **All field values** for the selected record, organized by section
- **Signal indicators** on flagged fields (colored dots showing severity)
- **Change history** if any patches have been drafted or applied
- **Patch authoring area** — This is where you draft corrections

**Key point:** The Record Inspector is where you do your actual work as an Analyst. You review field values, compare them against the source document, and draft corrections when something needs to change.

`[IMAGE: Record Inspector drawer open alongside the grid]`

---

## Scene 8: Patch Studio — Writing Corrections

When you find something that needs correcting, you author a patch. A patch is a structured change request with evidence.

**Every correction patch has four parts (the Evidence Pack):**

| Block | Alias | What to write |
|-------|-------|--------------|
| **Observation** | WHEN | What situation did you observe? "The payment frequency field says 'Annual' but the contract specifies quarterly payments." |
| **Expected** | THEN | What should it be? "Payment frequency should be 'Quarterly' per Section 4.2 of the agreement." |
| **Justification** | BECAUSE | Why is this change correct? "Source document Section 4.2 explicitly states 'Licensee shall pay quarterly royalties.'" |
| **Repro** | (steps) | How can someone verify this? "Open contract PDF page 12, Section 4.2, paragraph 3." (Required for Corrections unless an override is active.) |

For other patch types (Blacklist Flag, RFI), only the Justification block is required (minimum 10 characters).

**Patch lifecycle:**
1. **Draft** — You're still working on it. Only you can see it.
2. **Submitted** — You've sent it for review. The Verifier gets notified.
3. **At Verifier** — The Verifier is reviewing your evidence.
4. **Needs Clarification** — The Verifier has questions. You'll see an RFI to respond to.
5. **Approved** → **Promoted** → **Applied** — The correction flows through to become canonical truth.

**Key point:** No change happens without evidence. No self-approval. Every correction goes through at least one other person.

`[IMAGE: Patch Studio with evidence blocks filled in]`

---

## Scene 9: Contract Health Scores

Back on the Triage dashboard, you'll see Contract Health scores — a quick visual health check for each contract.

**Four health bands:**
- **Critical** (red) — Major issues, likely blockers
- **At Risk** (orange) — Significant issues that need attention
- **Watch** (yellow) — Minor issues, low priority
- **Healthy** (green) — No significant issues detected

**What drives the score:**
- Number and severity of pre-flight issues
- Missing required values
- Encoding quality
- Schema coverage (how well the data maps to known fields)

`[IMAGE: Contract health summary with colored bands]`

---

## Scene 10: Export and Handoff

When your work is done (corrections drafted, evidence attached, patches submitted), you can export the workbook.

**Two export options (bottom of sidebar):**
- **Export** — Clean workbook with your edits only. Good for quick handoffs.
- **Export Full** — Complete workbook with change log, signals, RFIs, and full audit trail. This is the governance artifact.

**Save to Drive** — Push the finalized workbook back to Google Drive with status-based naming: `{name}__{STATUS}__{date}__{workspace}.xlsx`

**Key point:** The exported file is the proof of work. It includes everything — what was changed, who changed it, when, and why. This is what makes governance auditable.

`[IMAGE: Export buttons in sidebar]`

---

## Quick Reference: Analyst Keyboard Shortcuts

| Action | How |
|--------|-----|
| Search records | `Cmd+K` (or click the search bar) |
| Navigate to Triage | Click "Triage" in sidebar |
| Navigate to Grid | Click "Record Inspector" in sidebar |
| Open a record detail | Click the magnifying glass in the Actions column |
| Open source document | Click the link icon in the Actions column |
| Switch grid sections | Click sheet tabs at top of grid |
| Toggle Evidence Viewer | Click "Evidence Viewer" tab in grid header |

---

## Glossary of Terms

| Term | What it means |
|------|--------------|
| **Patch** | A structured correction request with evidence |
| **RFI** | Request for Information — a question sent to someone about a record |
| **Signal** | An automated flag generated by the rules engine on a specific cell |
| **Pre-Flight** | Automated data quality checks run when data is loaded |
| **Semantic Pass** | Rule-based proposals generated by the system |
| **Evidence Pack** | The WHEN/THEN/BECAUSE justification attached to every patch |
| **Triage** | The dashboard showing all items needing attention |
| **Promotion** | The act of making a correction part of the canonical truth |
| **Sandbox** | Demo mode where you can experiment freely without affecting real data |
| **Config Pack** | The rules bundle that drives all signals and validations |

---

*Last updated: February 2026 — Orchestrate OS v2.53*
