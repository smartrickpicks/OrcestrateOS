# Feature Request: Schema Tree Editor (Admin Standardizer Tab)

Status: Proposed
Priority: High
Target: V2
Author: Product / Engineering
Date: 2026-02-08

---

## Summary

Transform the Admin Panel's **Standardizer tab** from a basic CSV normalizer into a full **Schema Tree Editor** — a visual, interactive JSON tree that lets Admins browse, edit, and govern the canonical data standard. The core goal is to manage schema evolution: when analysts upload columns that don't match the standard, Admins need to determine whether it's a renaming issue or a genuinely new data point requiring a tenant-specific rule.

This tab becomes the single place where the data standard lives, evolves, and gets approved.

---

## Problem Statement

Today, when an analyst uploads an Excel file with non-standard column names:
1. The system detects "unknown columns" via `resolveColumnMapping()` and shows them in the **Unknown Cols** tab
2. An Admin can see the original name, a normalized version, and sample values
3. But there's no way to **edit the standard itself**, **visualize the schema hierarchy**, or **approve changes** through a governed workflow
4. The canonical schema (`field_meta.json` with 442 fields) is a flat JSON file that must be regenerated via a build script — there's no in-app editing
5. When schema drift occurs (a column that doesn't match), there's no structured way to decide: "Is this a rename of an existing field, or a new field that needs a tenant-specific rule?"

---

## What This Feature Needs

### Data the Editor Must Display

The Schema Tree Editor needs to render and allow editing of the following data sources. These are the files an implementing agent must read and understand:

#### 1. Field Metadata — `rules/rules_bundle/field_meta.json`
The canonical field schema. 442 fields organized by contract section.

**Current structure**:
```json
{
  "version": "v1",
  "meta": {
    "generated_at_utc": "2026-02-05T04:43:09Z",
    "glossary_source": "Master Glossary [Holwerda, Data Dash].xlsx"
  },
  "fields": [
    {
      "sheet": "Accounts",
      "field_key": "account_number_c",
      "field_label": "Account Number",
      "definition": "",
      "return_format": "Text",
      "example_output": "",
      "requiredness": "not_needed",
      "options": [],
      "picklist": false,
      "source_sheet": "Account Fields Definitions"
    }
  ]
}
```

**Tree hierarchy**: `sheet` → fields within that contract section. Each field has properties (label, type, requiredness, picklist options, definition).

**What the tree should show**:
- Top level: contract sections (Accounts, Opportunities, Contracts, etc.)
- Second level: fields within each contract section (expandable)
- Third level: field properties (return_format, requiredness, options, definition, etc.)
- Editable leaf nodes for property values

#### 2. Hinge Groups — `rules/rules_bundle/hinge_groups.json`
Defines which fields are primary and secondary decision-critical fields per contract section.

**Current structure**:
```json
{
  "version": "v1",
  "meta": { ... },
  "hinges": [
    {
      "sheet": "Accounts",
      "type": "primary",
      "field_key": "account_name",
      "why": "Core identity anchor for all downstream joins"
    }
  ]
}
```

**Tree display**: Show hinge fields as tagged/badged nodes in the tree (e.g., a "PRIMARY" or "SECONDARY" badge next to hinge fields).

#### 3. Contract Section Order — `rules/rules_bundle/sheet_order.json`
Canonical ordering of contract sections with reasoning.

**Current structure**:
```json
{
  "version": "v1",
  "order": [
    {
      "order": 1,
      "sheet": "Accounts",
      "why": "Identity first. Fixing party/org data resolves the highest-volume errors...",
      "primary_outputs": "Validated account + entity identity"
    }
  ]
}
```

**Tree display**: Contract section order determines the top-level node ordering. The "why" and "primary_outputs" should be visible in a tooltip or expanded detail panel.

#### 4. QA Flags — `rules/rules_bundle/qa_flags.json`
QA validation flag definitions.

#### 5. Document Types — `config/document_types.json`
Document type classifications (5 types currently).

#### 6. Column Mapping Aliases — (embedded in `resolveColumnMapping()`)
The current column alias lists that map non-standard names to canonical names:
- `file_name` aliases: `filename`, `file name`, `contract file`, `contract file name`, `document`, `doc_name`
- `file_url` aliases: `fileurl`, `file url`, `url`, `contract source`, `contract url`, `pdf url`, `source`, `document_url`, `doc_url`, `link`

These should be **editable in the tree** so Admins can add new aliases without code changes.

#### 7. Unknown Columns Store — `localStorage key: unknown_columns`
Currently detected unknown columns from the most recent upload. This data should feed into the tree as "pending classification" nodes.

---

### Visual Tree Editor Requirements

#### Tree Structure (Collapsible JSON Tree)

```
▼ Standard v1 (root)
  ├── ▼ Accounts (32 fields) [Order: 1] [PRIMARY: account_name]
  │   ├── ▼ account_number_c
  │   │   ├── label: "Account Number"
  │   │   ├── type: Text
  │   │   ├── required: not_needed
  │   │   ├── picklist: false
  │   │   └── definition: ""
  │   ├── ▼ account_name ⚡ PRIMARY HINGE
  │   │   ├── label: "Account Name"
  │   │   ├── type: Text
  │   │   ├── required: required
  │   │   └── ...
  │   └── ▼ ⚠ billing_address_unknown  [PENDING - Unknown Column]
  │       ├── original_name: "Billing Address (Custom)"
  │       ├── sample_values: ["123 Main St", "456 Oak Ave"]
  │       ├── non_empty: 847 / 1200
  │       └── action: [Rename to existing ▾] [Add as new field] [Tenant rule] [Ignore]
  │
  ├── ▼ Opportunities (78 fields) [Order: 2]
  │   └── ...
  │
  ├── ▼ Column Aliases
  │   ├── ▼ file_name → ["filename", "file name", "contract file", ...]
  │   └── ▼ file_url → ["fileurl", "file url", "url", ...]
  │
  └── ▼ Schema Metadata
      ├── version: v1
      ├── generated_at: 2026-02-05T04:43:09Z
      └── field_count: 442
```

#### Interaction Model

- **Expand/Collapse** — Click `▼`/`▶` toggles to show/hide children at any level
- **Inline Editing** — Click any leaf value to edit it in-place (text input, dropdown for enums like `requiredness`)
- **Add Field** — "+" button at contract section level to add a new field with default properties
- **Add Contract Section** — "+" button at root level to add a new contract section
- **Delete** — Right-click or trash icon to remove a field (with confirmation)
- **Search/Filter** — Search bar at top to filter the tree by field key, label, or contract section name
- **Drag to Reorder** — Optional: drag contract sections to change order (updates `sheet_order.json`)

#### Color Coding

| Node State | Color | Meaning |
|------------|-------|---------|
| Standard field | Default (dark text) | Part of the canonical schema |
| Hinge field (primary) | Blue badge | Primary decision anchor |
| Hinge field (secondary) | Teal badge | Secondary decision field |
| Unknown/pending column | Orange/amber highlight | Detected in upload, not yet classified |
| Modified (unsaved) | Yellow dot indicator | Changed in this editing session |
| New (added) | Green dot indicator | Added in this editing session |
| Deleted (pending) | Red strikethrough | Marked for removal |

---

### Schema Drift Classification Workflow

When an unknown column is detected (from the existing Unknown Cols detection), it appears in the tree under its detected contract section with an amber highlight. The Admin has four actions:

#### Action 1: Rename to Existing Field
The unknown column is just a different name for an existing canonical field.
- Admin selects "Rename to existing" and picks the target field from a dropdown
- This adds the unknown column name as a new **alias** for that field
- Future uploads with this column name will automatically map to the canonical field
- Produces an **alias patch** artifact

#### Action 2: Add as New Canonical Field
The unknown column represents genuinely new data that should be part of the standard for everyone.
- Admin fills in field properties (label, type, requiredness, definition, picklist options)
- The field is added to the canonical `field_meta.json`
- Produces a **schema patch** artifact

#### Action 3: Create Tenant Rule
The unknown column is valid but specific to one tenant/division — not universal.
- Admin creates a tenant-scoped rule that maps this column for a specific `tenant_id` + `division_id`
- The rule is stored separately (not in the global schema)
- Other tenants don't see this field
- Produces a **tenant rule** artifact

#### Action 4: Ignore / Suppress
The column is noise (e.g., an Excel formula artifact, a temporary column).
- Admin marks it as "ignored"
- It won't trigger the unknown column warning on future uploads from this tenant
- Produces a **suppression rule** artifact

---

### Load / Edit / Approve Workflow

#### Loading the Standard
1. On tab open, automatically load all rules bundle files (`field_meta.json`, `hinge_groups.json`, `sheet_order.json`, `qa_flags.json`) and `document_types.json`
2. Merge unknown columns from the current session (if any exist in `localStorage`)
3. Render the tree

#### Editing
1. All edits are tracked in a **change buffer** (in-memory diff between original and current state)
2. A "Pending Changes" counter shows how many modifications exist
3. Each change is categorized: field_added, field_modified, field_deleted, alias_added, tenant_rule_created, field_ignored
4. Changes can be reverted individually (undo per-node)

#### Saving / Approving
1. **Save Draft** — Persists the change buffer to IndexedDB (survives page reload)
2. **Preview Changes** — Shows a diff view (before/after) for all pending changes
3. **Export as Patch** — Generates a JSON patch artifact in the established `config_pack.patch.json` format, suitable for review in the Patch Console
4. **Apply to Local** — Applies changes to the in-memory rules bundle immediately (for testing with current dataset)
5. **Approve & Commit** — (Future / with backend) Writes changes to the rules bundle files on disk

#### Audit Trail
Every schema change emits an audit event to the `AuditTimeline` store:
- `schema_field_added` — New field added to standard
- `schema_field_modified` — Field properties changed
- `schema_field_deleted` — Field removed from standard
- `schema_alias_added` — New column alias registered
- `schema_tenant_rule_created` — Tenant-specific mapping rule created
- `schema_drift_ignored` — Unknown column suppressed

---

## Relationship to Existing Features

### Replaces / Subsumes
- **Current Standardizer tab** — The CSV paste/upload normalizer is replaced by the tree editor. The CSV standardization function (`runStandardizer()`) can remain as a utility but is no longer the primary purpose of this tab.
- **Unknown Cols tab** — Schema drift classification moves into the tree editor. The Unknown Cols tab becomes redundant and can be merged into this view.

### Integrates With
- **Signal Engine** — When the schema changes (new required field, new picklist), the signal engine automatically picks up the updated rules bundle on next dataset load
- **Column Mapping** — New aliases registered in the tree editor feed into `resolveColumnMapping()` so future uploads auto-map correctly
- **Patch Studio** — Schema patches follow the same patch lifecycle (draft → preflight → review → approve) as data patches
- **Audit Timeline** — Schema changes are tracked alongside all other governance actions

### Does Not Change
- **Data Loader Pipeline** — Excel upload, SheetJS parsing, workbook population all remain the same (documented in `docs/ingestion/DATA_LOADER_PIPELINE.md`)
- **Grid Rendering** — No changes to how the grid displays data
- **Role Permissions** — Only Admins can access the Standardizer tab (existing RBAC)

---

## Files an Implementing Agent Must Read

| Priority | File / Document | Why |
|----------|----------------|-----|
| **Critical** | `ui/viewer/index.html` | Single-file app — all HTML, CSS, JS lives here. Search for `admin-tab-standardizer`, `runStandardizer`, `resolveColumnMapping`, `unknown_columns` |
| **Critical** | `rules/rules_bundle/field_meta.json` | The canonical schema (442 fields). This is what the tree renders. |
| **Critical** | `rules/rules_bundle/hinge_groups.json` | Hinge field classifications (47 hinges). Drives badge display in tree. |
| **Critical** | `rules/rules_bundle/sheet_order.json` | Contract section ordering (8 contract sections). Drives top-level tree node order. |
| **Critical** | `rules/rules_bundle/qa_flags.json` | QA flag definitions. Part of the tree. |
| **High** | `config/document_types.json` | Document type definitions (5 types). Part of the tree. |
| **High** | `docs/ingestion/DATA_LOADER_PIPELINE.md` | How uploaded data flows through the system — context for where schema drift is detected |
| **High** | `docs/ui/views/data_source_view.md` | Data Source UX contract — context for how data enters the system |
| **High** | `docs/rules/rules_bundle.md` | How the rules bundle is structured, generated, and validated |
| **Medium** | `docs/AUDIT_LOG.md` | Audit timeline system — schema changes must emit audit events |
| **Medium** | `docs/ingestion/INGESTION_DOCTRINE.md` | Folder conventions for inbound/outbound artifacts |
| **Medium** | `docs/ui/ui_principles.md` | UI governance rules that the tree editor must follow |
| **Medium** | `replit.md` | Project architecture summary — overall system context |
| **Reference** | `docs/INDEX.md` | Documentation index — find any other doc quickly |

---

## Key Functions in the Codebase

| Function | Approx. Line | Relevance |
|----------|-------------|-----------|
| `resolveColumnMapping(headers)` | ~6417 | Current column alias logic — tree editor replaces this with editable aliases |
| `applyColumnMapping(rows, headers, mapping)` | ~6465 | Applies column mapping — must read new aliases from tree editor |
| `generateSignalsForDataset()` | ~13991 | Signal engine — uses `field_meta.json` for validation; tree editor changes propagate here |
| `generateCellSignals(row, fieldKey, sheetName, recordId)` | (search) | Per-cell signal generation — uses requiredness, picklist options from field_meta |
| `runStandardizer()` | ~8708 | Current standardizer logic — will be replaced/augmented |
| `refreshUnknownColumnsTable()` | (search) | Current unknown columns detection — data feeds into tree editor |
| `switchAdminTab(tab)` | ~11288 | Tab switching — standardizer tab is one of: governance, users, patch-queue, config, inspector, standardizer, patch-console, evidence, unknown-cols |
| `SessionDB` module | ~4556 | IndexedDB storage — tree editor drafts should use this for persistence |
| `AuditTimeline` module | ~4818 | Audit event storage — schema changes must emit events here |

---

## Implementation Notes

### No External Libraries Required
The tree editor should be built with vanilla JS (consistent with the rest of the codebase). No React, no Vue, no tree library. Use recursive DOM construction with `<details>`/`<summary>` elements or custom expand/collapse divs.

### Storage Strategy
- **Draft changes**: Store in IndexedDB via `SessionDB` (new object store or extend existing)
- **Applied changes**: Write to in-memory `rulesBundleCache` for immediate effect
- **Exported patches**: JSON artifacts in the established patch format
- **Tenant rules**: New localStorage key or IndexedDB store for tenant-scoped rules

### The "Standard" Is the Source of Truth
The tree editor is editing the **standard itself** — `field_meta.json` and related files. Changes here cascade to:
- Signal generation (new required fields → new `MISSING_REQUIRED` signals)
- Picklist validation (new options → `PICKLIST_INVALID` signals updated)
- Column mapping (new aliases → auto-mapping on upload)
- Unknown column detection (new fields → fewer unknowns on next upload)

### Salesforce Context
The primary use case driving this feature is Salesforce data governance. Different Salesforce orgs have different custom fields (e.g., `billing_address_c` vs `billing_address__c` vs `Billing_Address`). The tree editor lets Admins:
1. See the canonical Salesforce field standard
2. Identify schema drift from a specific org's export
3. Decide: rename (alias), add to standard, create tenant rule, or ignore
4. Export the decision as a reviewable patch artifact

---

## Success Criteria

1. Admin can open the Standardizer tab and see a fully rendered, collapsible tree of the canonical schema (all 442 fields organized by 8 contract sections)
2. Unknown columns from the current dataset appear inline in the tree with amber highlighting
3. Admin can classify each unknown column (rename/add/tenant rule/ignore) with a clear UI action
4. All edits are tracked, diffable, and exportable as a patch artifact
5. Changes can be applied locally for immediate testing with the current dataset
6. Schema changes emit audit events to the Audit Timeline
7. The tree loads in under 2 seconds for the full 442-field schema
8. No external JS libraries — pure vanilla JS, consistent with the existing codebase

---

## Open Questions for Product / Domain Expert

1. **Tenant rule storage**: Where should tenant-specific rules live? Separate JSON file per tenant, or a single `tenant_rules.json` with tenant_id scoping?
2. **Approval workflow**: Should schema patches go through the same 11-status lifecycle as data patches, or a simplified approve/reject flow?
3. **Version history**: Should the tree editor maintain a version history of the schema (v1, v2, v3...) or just track individual changes?
4. **Conflict resolution**: If two Admins edit the schema simultaneously (future multi-user scenario), what's the merge strategy?
5. **Google Drive sync**: When Drive integration arrives, should schema changes auto-sync to a shared Drive location?
