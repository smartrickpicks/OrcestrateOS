# Control Board Viewer

## Overview
A read-only, single-file HTML viewer for sf_packet artifacts. No build step, no dependencies, no external network requests.

**Version:** 0.5

## How to Open

### Option 1: Local file (simple)
Open `ui/viewer/index.html` directly in your browser.

**Note:** Due to browser security policies, fetching local JSON files may be blocked. Use Option 2 if tables don't load.

### Option 2: Local server (recommended)
From the repository root, run:

```bash
python3 -m http.server 8080
```

Then open: http://localhost:8080/ui/viewer/index.html

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

### Selectable Records (v0.5)

In the Issues, Actions, and Change Log tabs, each row has a checkbox for selection:

| Control | Action |
|---------|--------|
| **Checkbox** | Toggle individual record selection |
| **Select All** | Select all records in the current tab |
| **Clear** | Deselect all records in the current tab |
| **Add Selected to Patch** | Add selected records to the Patch Studio draft |

Selection persists within the current workbench session.

### Patch Studio Lite (v0.5)

Access Patch Studio by clicking the green "Patch Studio" button in the Record Workbench.

#### Draft Fields
| Field | Description |
|-------|-------------|
| **Base Version** | Version this patch applies to (e.g., "0.1.0") |
| **Author** | Your email or identifier |
| **Rationale** | Description of why this patch is needed |

#### Changes Preview
- Shows all records added to the patch draft
- Sorted by severity (blocking > warning > info), then sheet/field
- Remove individual items with the × button
- Clear all changes with the "Clear All" button

#### Copy Outputs

| Button | Output Format |
|--------|---------------|
| **Copy Full Patch Draft (JSON)** | Complete `config_pack.patch.json` structure with sorted keys |
| **Copy Rule Mapping (JSON)** | Array of rule objects in patch-rule shape |
| **Copy Grouped Rule Draft** | WHEN/THEN/BECAUSE text with grouped rules |

All outputs are deterministic with sorted keys and stable ordering.

### Evidence Helper (v0.5)

Located in Patch Studio, provides copy-only buttons for:

| Button | Content |
|--------|---------|
| **Smoke Baseline** | Baseline smoke test command |
| **Smoke Edge** | Edge case smoke test command |
| **Evidence Template** | Markdown template with placeholders for SHA256, commit, verification checklist |

### Copy PR Kit

| Button | Output |
|--------|--------|
| **Copy JSON** | Current tab's data as JSON (sorted keys) |
| **Copy PR Summary** | Markdown summary with title, WHY section, affected artifacts |
| **Copy Rule Draft** | WHEN / THEN / BECAUSE format for each issue |

### Determinism Guarantees

All outputs follow these ordering rules:
- **Severity order:** blocking > warning > info
- **Join triplet:** contract_key → file_url → file_name (nulls last)
- **Secondary sort:** sheet, field, then type-specific fields
- **JSON:** All keys sorted alphabetically
- **Rule IDs:** Based on primary key + index (no timestamps)

### State Persistence
The viewer persists your selection in localStorage:
- Selected join identity
- Active tab
- Source type

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

### Building a Patch Draft

1. Click any row in a table to open the Record Workbench
2. Navigate to the Issues or Actions tab
3. Check the records you want to include in the patch
4. Click "Add Selected to Patch"
5. Patch Studio opens showing your selected changes
6. Fill in Base Version, Author, and Rationale
7. Click "Copy Full Patch Draft (JSON)" to copy the complete patch
8. Paste into your patch file and review

### Generating Evidence

1. After creating a patch, use Evidence Helper buttons
2. Copy smoke commands and run them in terminal
3. Copy Evidence Template and fill in commit SHA, file hash
4. Include evidence in your PR

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
- **State persistence**: Selection saved to localStorage

## Version History

| Version | Features |
|---------|----------|
| 0.5 | Patch Studio Lite (selectable records, grouped rule builder, full patch draft, evidence helper) |
| 0.4 | Universal drilldown, Copy PR Kit, PRIMARY key indicator, duplicate identity warning |
| 0.3 | Record Workbench with tabbed drawer, join identity matching, localStorage persistence |
| 0.2 | Toolbar with copy-only commands, filters, basic drilldown |
| 0.1 | Initial viewer with summary, tables |
