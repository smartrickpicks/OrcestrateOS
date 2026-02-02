# Control Board Viewer

## Overview
A read-only, single-file HTML viewer for sf_packet artifacts. No build step, no dependencies, no external network requests.

**Version:** 1.1.1

## How to Open

### In Replit

1. Click the **Run** button (or run the "Viewer Server" workflow)
2. The Webview pane will open - navigate to `/ui/viewer/index.html`
3. Or use the URL shown in the console output

**Note:** Replit may show "app not running" briefly before the static server starts. This is expected for static HTML - the viewer has no backend framework, just a simple file server.

### Run Locally

From the repository root, run:

```bash
bash scripts/serve_viewer.sh
```

Then open: http://localhost:5000/ui/viewer/index.html

### Open File Directly (limited)

Open `ui/viewer/index.html` directly in your browser.

**Note:** Due to browser security policies, fetching local JSON files may be blocked. Use the serve script if tables don't load.

## Artifacts Read

The viewer reads sf_packet JSON files in this order:

| Priority | Path | Description |
|----------|------|-------------|
| 1 | `out/sf_packet.preview.json` | Generated preview output |
| 2 | `examples/expected_outputs/sf_packet.example.json` | Fallback example data |

Paths are relative to the repository root.

## Features

### Toolbar

The toolbar provides quick access to common commands:

| Button | Command |
|--------|---------|
| Validate | Validate configuration files (base + patch) |
| Preview Baseline | Generate preview with baseline example data |
| Preview Edge | Generate preview with edge case data |
| Smoke Baseline | Run smoke test against baseline expected output |
| Smoke Edge | Run smoke test against edge expected output |

**Copy-Only Default:** Clicking any toolbar button automatically copies the command to clipboard.

### Filters

Located below the toolbar, filters allow you to narrow down table results:

| Filter | Description |
|--------|-------------|
| **Search** | Free-text search across all fields in all tables |
| **Severity Chips** | Toggle visibility of blocking/warning/info severity rows |
| **Status Chips** | Toggle visibility of ready/needs_review/blocked status rows |
| **Subtype Dropdown** | Filter Contract Results by detected_subtype |

### Universal Drilldown

Click any row in **any table** (Contract Results, Issues, or Field Actions) to open the Record Workbench drawer.

### Record Workbench

#### Join Identity with PRIMARY Indicator
The drawer header displays a **join identity pill** with visual emphasis on the PRIMARY key:
- **Green (PRIMARY):** The first non-null key in the join priority order
- **Gray (fallback):** Secondary keys in the identity

Priority order: `contract_key` → `file_url` → `file_name`

#### Tabs
The workbench has four tabs:

| Tab | Content |
|-----|---------|
| **Contract** | Full JSON of the matching contract record |
| **Issues** | All `sf_issues` rows matching the join identity |
| **Actions** | All `sf_field_actions` rows matching the join identity |
| **Change Log** | All `sf_change_log` rows matching the join identity |

### Selectable Records

In the Issues, Actions, and Change Log tabs, each row has a checkbox for selection:

| Control | Action |
|---------|--------|
| **Checkbox** | Toggle individual record selection |
| **Select All** | Select all records in the current tab |
| **Clear** | Deselect all records in the current tab |
| **Add Selected to Patch** | Add selected records to the Patch Studio draft |

Selection persists within the current workbench session.

### Patch Studio (v0.6)

Access Patch Studio by clicking the green "Patch Studio" button in the Record Workbench. Patch Studio now has two tabs: **Draft** and **Preflight**.

#### Draft Tab

| Field | Description |
|-------|-------------|
| **Base Version** | Version this patch applies to (e.g., "0.1.0") |
| **Author** | Your email or identifier |
| **Rationale** | Description of why this patch is needed |

**Changes Preview:**
- Shows all records added to the patch draft
- Sorted by severity (blocking > warning > info), then sheet/field
- Remove individual items with the × button
- Clear all changes with the "Clear All" button

**Copy Outputs:**

| Button | Output Format |
|--------|---------------|
| **Copy Full Patch Draft (JSON)** | Complete `config_pack.patch.json` structure with sorted keys |
| **Copy Rule Mapping (JSON)** | Array of rule objects in patch-rule shape |
| **Copy Grouped Rule Draft** | WHEN/THEN/BECAUSE text with grouped rules |

#### Preflight Tab (v0.6)

The Preflight Gate ensures your patch draft is validated before PR submission.

**4-Step Checklist:**

| Step | Description |
|------|-------------|
| 1. Base Version Check | Verify base.version matches patch.base_version |
| 2. Validation Report | Paste validator output to confirm config is valid |
| 3. Conflict Check | Confirm no rule conflicts exist |
| 4. Smoke Evidence | Paste smoke test results (baseline + optional edge) |

**Checklist Status Chips:**
- **Green (pass):** Evidence parsed successfully, step satisfied
- **Yellow (warn):** Evidence needs manual review
- **Red (fail):** Validation or smoke test failed
- **Gray (pending):** No evidence provided yet

**Paste-In Evidence Inputs:**
Each step has a text input where you paste terminal output. Click "Parse" to extract structured data:

| Input | What to Paste |
|-------|---------------|
| Base Version | Version string (e.g., "0.1.0") or JSON with version field |
| Validation Report | Output from `python3 local_runner/validate_config.py` |
| Conflict Check | Conflict report text, or type "reviewed" for manual confirmation |
| Smoke Baseline | Output from `bash scripts/replit_smoke.sh` |
| Smoke Edge | Output from `bash scripts/replit_smoke.sh edge` (optional) |
| SHA256 | Optional hash values for verification |

**Parsed Results:**
When parsing succeeds, a result panel shows extracted fields:
- Validation: status, base.version, patch.base_version, changes_count
- Conflicts: rendered as a table if any are found
- Smoke: PASS/FAIL status for baseline and edge

**Reset Evidence:**
Click "Reset All Evidence" to clear all preflight inputs without affecting the patch draft.

### Evidence Helper

Located in the Draft tab, provides copy-only buttons for:

| Button | Content |
|--------|---------|
| **Smoke Baseline** | Baseline smoke test command |
| **Smoke Edge** | Edge case smoke test command |
| **Evidence Template** | Markdown template with placeholders for SHA256, commit, verification checklist |

### Copy PR Kit (with Evidence)

The "Copy PR Summary" button now generates a PR summary that includes an **Evidence section** populated from Preflight data:

| Field | Source |
|-------|--------|
| base.version | From Preflight or Draft field |
| patch.base_version | From parsed validation report or Draft field |
| Smoke Baseline | PASS/FAIL from parsed smoke output |
| Smoke Edge | PASS/FAIL or N/A if not provided |
| SHA256 | From preflight SHA256 input |

### Determinism Guarantees

All outputs follow these ordering rules:
- **Severity order:** blocking > warning > info
- **Join triplet:** contract_key → file_url → file_name (nulls last)
- **Secondary sort:** sheet, field, then type-specific fields
- **JSON:** All keys sorted alphabetically
- **Rule IDs:** Based on per-record primary key + index (no timestamps)

### State Persistence
The viewer persists your data in localStorage:
- Selected join identity (STORAGE_KEY)
- Patch draft including changes, author, rationale (PATCH_STORAGE_KEY)
- Preflight evidence blobs and parsed fields (PREFLIGHT_STORAGE_KEY)

### Summary Cards
Displays counts from `sf_summary`:
- Total contracts
- Ready (green)
- Needs Review (orange)
- Blocked (red)

### Tables
Three main tables with deterministic sorting:

1. **Contract Results** - `sf_contract_results`
   - Sorted by: contract_key (nulls last), file_url, file_name

2. **Issues** - `sf_issues`
   - Sorted by: severity, join triplet, sheet, field, issue_type

3. **Field Actions** - `sf_field_actions`
   - Sorted by: severity, join triplet, sheet, field, action

## Workflow

### Building a Patch Draft with Preflight Validation

1. Click any row in a table to open the Record Workbench
2. Navigate to the Issues or Actions tab
3. Check the records you want to include in the patch
4. Click "Add Selected to Patch" to open Patch Studio
5. Fill in Base Version, Author, and Rationale in the Draft tab
6. Switch to the **Preflight** tab
7. Run validation in your terminal and paste the output
8. Click "Parse" for each evidence input
9. Verify all 4 checklist steps show green or yellow status
10. Switch back to Draft tab and click "Copy Full Patch Draft (JSON)"
11. Use "Copy PR Summary" to get a PR description with evidence included

### Generating Evidence

1. Use Evidence Helper buttons (Draft tab) to copy smoke commands
2. Run commands in terminal
3. Switch to Preflight tab and paste outputs
4. Click Parse to extract structured data
5. Copy PR Summary includes populated Evidence section

## Files

| File | Description |
|------|-------------|
| `index.html` | The viewer (single file, no build step) |
| `run_commands.json` | Canonical commands for toolbar buttons |
| `sample_data_links.json` | Documented artifact paths |
| `README.md` | This file |

## Technical Details

- **No build step**: Open index.html directly
- **No dependencies**: Vanilla HTML, CSS, JavaScript
- **No network requests**: All data loaded from local filesystem
- **No file writes**: All output is copy-to-clipboard only
- **Deterministic display**: Sorting matches run_local.py output ordering
- **Keyboard shortcuts**: Press `Escape` to close modals, drawers, and Patch Studio
- **State persistence**: Selection, patch draft, and preflight evidence saved to localStorage

### Comparison Mode (v0.7)

Compare two sf_packet artifacts to analyze changes between versions.

**Session Loader:**
Click "Show" in the Session Loader panel to reveal artifact path inputs:

| Field | Description |
|-------|-------------|
| Primary Artifact Path | The main artifact to display (default: out/sf_packet.preview.json) |
| Comparison Artifact Path | Optional previous version for delta analysis |

**Load/Clear Buttons:**
- **Load**: Fetches both artifacts and computes deltas
- **Clear Compare**: Removes comparison data, shows primary only

**Delta Summary Cards:**
When a comparison artifact is loaded, the Delta Summary section appears showing:

| Card | Description |
|------|-------------|
| Contracts | Change in total contract count |
| Ready | Change in ready status count |
| Needs Review | Change in needs_review count |
| Blocked | Change in blocked count |
| Issues Added | New issues not in comparison |
| Issues Changed | Issues with modified content |
| Issues Removed | Issues no longer present |
| Actions Added | New field actions not in comparison |
| Actions Removed | Field actions no longer present |

**Row Change Indicators:**
Tables display visual indicators for row-level changes:

| Color | Marker | Meaning |
|-------|--------|---------|
| Green (+) | `row-added` | New row not in comparison artifact |
| Orange (~) | `row-changed` | Row exists but content differs |
| Red strikethrough (-) | `row-removed` | Row in comparison but not in primary |

**Change Detection Logic:**
- Join identity: `contract_key|file_url|file_name` (plus sheet/field/type for issues/actions)
- Content hash: JSON.stringify with sorted keys
- Added: join key in primary but not in comparison
- Changed: join key in both but different content hash
- Removed: join key in comparison but not in primary

**Copy Delta Summary:**
Click "Copy Delta Summary (Markdown)" to copy a formatted markdown table of all delta statistics.

## Version History

### Config + Patch Inspector (v0.8)

Inspect base config and patch files to view ruleset semantic changes.

**Ruleset Loader Panel:**
Click "Show" in the Config + Patch Inspector panel to reveal config path inputs:

| Field | Description |
|-------|-------------|
| Base Config Path | Path to base config (default: config/config_pack.base.json) |
| Patch Path | Path to patch file (default: config/config_pack.example.patch.json) |

**Load/Clear Buttons:**
- **Load Config**: Fetches both files and renders the ruleset delta
- **Clear**: Removes loaded config data

**Patch Summary:**
Displays key patch metadata:

| Field | Description |
|-------|-------------|
| base.version | Version from base config |
| patch.base_version | Target version in patch |
| Author | Patch author identifier |
| Rationale | Description of why patch is needed |
| Changes Count | Number of changes in patch |

**Version Match Chip:**
- **GREEN (MATCH)**: base.version equals patch.base_version
- **RED (MISMATCH)**: Versions differ - blocks Preflight Base Version Check

**Ruleset Delta Counts:**
Shows Added/Deprecated counts per target:
- salesforce_rules
- qa_rules
- resolver_rules

**Changes[] Table:**
Deterministic table of patch changes with columns:

| Column | Description |
|--------|-------------|
| Action | add_rule or deprecate_rule |
| Target | Target ruleset (salesforce/qa/resolver) |
| Rule ID | Rule identifier (if any) |
| When | Condition tuple (sheet.field operator value) |
| Then | Action(s) to perform |
| Severity | blocking/warning/info |

**Copy Ruleset Delta Markdown:**
Click to copy a PR-ready markdown description of semantic changes.

**Preflight Integration:**
When configs are loaded and versions match, the Preflight Base Version Check is automatically populated.

**Deterministic Sorting:**
Changes are sorted by:
1. target asc
2. action asc
3. rule_id asc (nulls last)
4. when.sheet asc
5. when.field asc
6. severity order (blocking > warning > info)
7. then[0].sheet asc
8. then[0].field asc

## Version History

### How to Add Data Source in Static Mode (v1.1.1)

Since the viewer runs entirely in the browser with no backend, you need to provide data via one of these methods:

**Method 1: Paste JSON**
1. Click "Data Source" to open the panel
2. Select the "Paste JSON" tab
3. Copy your sf_packet JSON and paste it into the textarea
4. Click "Load from Paste"

**Method 2: Drag-and-Drop File**
1. Click "Data Source" to open the panel
2. Select the "Drop File" tab
3. Drag your sf_packet.json file onto the drop zone (or click to browse)
4. Click "Load from File"

**Method 3: Path Hint (Reference Only)**
- The "Path Hint" tab shows a path input but cannot actually load files in static mode
- Use this to document which path you're working with
- A warning reminds you to use Paste or Drop for actual data

**Session Persistence:**
- Enable "Remember in this browser" to persist loaded data to localStorage
- Data is restored automatically on next visit
- Use "Reset Session" to clear artifacts (patch draft is preserved)

**Session Status Chip:**
| Status | Meaning |
|--------|---------|
| NOT LOADED | No data in memory |
| LOADED | Data loaded via paste/drop |
| FALLBACK | Using bundled example data |

### Upload-First Flow + Modal Wizards (v1.1)

The viewer now starts with a clear "Data Source" action and uses modal wizards for configuration, giving a more product-like feel.

**Operator Journey:**
1. **Data Source** - Click "Data Source" to add or switch data sources
2. **Triage** - View summary cards, filter issues, and drill down into records
3. **Workbench** - Click any record row to open the Workbench drawer for details
4. **Build Patch** - Click "Build Patch" button to add selected issues/actions to a patch
5. **Preflight** - Validate the patch using the Preflight Gate checklist
6. **Copy Artifacts** - Copy patch JSON, PR summary, and evidence for submission

**Modals:**
| Modal | Button | Purpose |
|-------|--------|---------|
| Data Source | Data Source | Add or switch data source |
| Ruleset | Ruleset | Configure base config + patch paths |
| Compare | Compare | Load comparison artifact for delta view |
| Run | Run Commands | Copy validation/preview/smoke commands |

**Pages:**
| Page | Path | Purpose |
|------|------|---------|
| Triage | #/triage | Summary cards, filters, issues/actions queues, workbench drilldown |
| Patch Studio | #/patch | Preflight Gate, Patch Draft Builder, copy outputs |
| Review | #/review | Config+Patch Inspector, Comparison Mode (Reviewer mode only) |

**Mode Toggle:**
| Mode | Description |
|------|-------------|
| Operator | Default view for triaging and building patches |
| Reviewer | Unlocks Review page for config inspection and comparison |
| Analyst | Focused view for data analysis |

### Multi-Page Navigation + Mode Toggle (v1.0)

Legacy: 4-page navigation structure with hash-based routing.

### Session + Stream Model (v0.9)

Conceptual UI-only model for future continuous/streaming pipeline semantics.

**Session Timeline Panel:**
Click "Show" in the Session + Stream Model panel to view:

**Never-Stop Flow Concept:**
Explains the "open faucet" model where:
- Good records (CONSOLIDATED) flow through immediately
- Partial records wait until missing data arrives
- Blocked records require manual intervention
- No backlogs - issues are isolated, not blocking

**Record State Model:**
| State | Condition | Flow Behavior |
|-------|-----------|---------------|
| CONSOLIDATED | No blocking/warning issues | Passes through |
| PARTIAL | Has warnings only | Usable but incomplete |
| WAITING | Missing data warnings | Held for later |
| BLOCKED | Blocking issues | Manual fix required |

**State Derivation:**
States are computed deterministically from issues:
1. If any blocking issue → BLOCKED
2. Else if missing data + warning → WAITING
3. Else if any warning → PARTIAL
4. Else → CONSOLIDATED

**Session Timeline:**
Simulates how records would arrive in ordered ingest waves:
- Session index and timestamp
- Record count and state distribution
- Reconsolidation count from previous sessions

**Reconsolidation Rules:**
| From | Condition | To |
|------|-----------|-----|
| PARTIAL | Warnings resolved | CONSOLIDATED |
| WAITING | Data arrives | PARTIAL/CONSOLIDATED |
| BLOCKED | Manual fix | CONSOLIDATED |
| CONSOLIDATED | New blocking issue | BLOCKED |

**Copy Stream Semantics Markdown:**
Click to copy a PR-ready explanation of the stream model.

## Version History

| Version | Features |
|---------|----------|
| 1.1.1 | Loader Simulation (Paste JSON, Drag-drop file, Path hint; Session status chip; localStorage persistence; Reset Session) |
| 1.1 | Upload-First Flow + Modal Wizards (Load Data CTA, Data Source/Ruleset/Compare/Run modals, triage-first landing, contextual patching) |
| 1.0 | Multi-Page Navigation + Mode Toggle (Run/Triage/Patch Studio/Review pages, Operator/Reviewer/Analyst modes) |
| 0.9 | Session + Stream Model (Session Timeline, Record States, Never-Stop Flow, Reconsolidation Rules, Copy Stream Semantics) |
| 0.8 | Config + Patch Inspector (Ruleset Loader, Patch Summary, Version Match, Changes Table, Ruleset Delta Counts, Copy Ruleset Delta Markdown, Preflight Integration) |
| 0.7 | Comparison Mode (Session Loader, Delta Summary Cards, row-level change indicators, Copy Delta Summary) |
| 0.6 | Preflight Gate (4-step validation checklist, paste-in evidence parsing, PR Summary with Evidence section, localStorage persistence for preflight + patch draft) |
| 0.5 | Patch Studio Lite (selectable records, grouped rule builder, full patch draft, evidence helper) |
| 0.4 | Universal drilldown, Copy PR Kit, PRIMARY key indicator, duplicate identity warning |
| 0.3 | Record Workbench with tabbed drawer, join identity matching, localStorage persistence |
| 0.2 | Toolbar with copy-only commands, filters, basic drilldown |
| 0.1 | Initial viewer with summary, tables |
