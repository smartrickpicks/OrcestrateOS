# Rules Bundle Overview

The rules bundle is a collection of JSON configuration files that define semantic field metadata, hinge groupings, and contract section ordering for the Orchestrate OS viewer application.

## Purpose

The rules bundle provides:
- **Field metadata** for semantic understanding of dataset fields
- **Hinge groupings** to identify primary and secondary decision-critical fields
- **Contract section ordering** for consistent navigation across views

The bundle is loaded on application startup and cached in memory for fast access during Field Inspector rendering and other semantic operations.

## Bundle Files

| File | Purpose | Record Count |
|------|---------|--------------|
| `field_meta.json` | Field definitions with labels, types, and validation rules | ~442 fields |
| `hinge_groups.json` | Primary/Secondary hinge field classifications per contract section | ~47 hinges |
| `sheet_order.json` | Canonical ordering of contract sections for navigation and display | 8 contract sections |

### Additional Reference Files

| File | Purpose |
|------|---------|
| `sheet_aliases.json` | Maps contract section name variations to canonical names |
| `opportunity_field_catalog.json` | Extended field catalog for Opportunity contract section |
| `qa_flags.json` | QA flag definitions and severity levels |
| `dealtype_matrix.json` | Deal type classification rules |
| `knowledge_keepers.json` | Subject matter expert routing rules |
| `parent_child_map.json` | Parent-child record relationships |
| `crosstab_parent_child_seed.json` | Crosstab seed data for parent-child views |

## JSON Schema Location

JSON schemas for bundle validation are located in:
```
rules/rules_bundle/schemas/
```

All bundle files must conform to their respective schemas for the application to load them correctly.

## How to Regenerate

The rules bundle is generated from source configuration files. The original build script (`scripts/build_rules_bundle.py`) is not present in the current repo. Rules bundle JSON files are maintained directly via the Schema Tree Editor in the Admin panel or by manual editing.

> **TODO**: `scripts/build_rules_bundle.py` — Not found. If automated regeneration from the Master Glossary XLSX is needed, this script must be recreated. The `glossary_source` path in each rules bundle JSON meta block is historical provenance pointing to the original local source file.

```bash
# Historical reference (script not found):
# python scripts/build_rules_bundle.py
```

### Source Files

| Bundle File | Source |
|-------------|--------|
| `field_meta.json` | Master Glossary spreadsheet |
| `hinge_groups.json` | Hinge Configuration document |
| `sheet_order.json` | Contract Section Order configuration |

### Build Requirements

- Python 3.x (standard library only)
- Source configuration files must be in expected format
- Output directory: `rules/rules_bundle/`

## Loader Behavior

The viewer application loads the bundle on `DOMContentLoaded`:

```javascript
// Loader sequence
1. Fetch /rules/rules_bundle/field_meta.json
2. Fetch /rules/rules_bundle/hinge_groups.json
3. Fetch /rules/rules_bundle/sheet_order.json
4. Cache in rulesBundleCache object
5. Set rulesBundleCache.loaded = true
```

### Fallback Behavior

If bundle loading fails:
- `rulesBundleCache.loaded` remains `false`
- Field Inspector falls back to legacy schema-based ordering
- Console warning is logged

## Usage in Application

### Field Inspector Ordering

When the bundle is loaded, fields are ordered as:

1. **Account Name** (always first, matches ACCOUNT_NAME_ALIASES)
2. **Primary Hinge Fields** (in hinge definition order)
3. **Secondary Hinge Fields** (in hinge definition order)
4. **Other Fields** (alphabetically sorted)

### Key Matching

Field keys are normalized for matching:
- Lowercase conversion
- Special characters removed
- Case-insensitive comparison

This ensures `Account_Name`, `account_name`, and `Account_Name_c` all match correctly.

## Server Configuration

The FastAPI server mounts the rules bundle directory for static serving:

```python
app.mount("/rules", StaticFiles(directory="rules"), name="rules")
```

Bundle files are accessible at:
- `/rules/rules_bundle/field_meta.json`
- `/rules/rules_bundle/hinge_groups.json`
- `/rules/rules_bundle/sheet_order.json`

## Strict Schema Requirement

All bundle JSON files must:
- Be valid JSON
- Conform to their respective schemas
- Contain no trailing commas or comments
- Use UTF-8 encoding

Invalid bundle files will cause the loader to fail, triggering fallback behavior.

## References

- [Record Inspection View](../ui/views/single_row_review_view.md) - Field Inspector ordering usage
- [Field Inspector Patch Flow](../ui/views/single_row_review_field_inspector_patch_flow.md)
