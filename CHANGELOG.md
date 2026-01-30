# CHANGELOG

## Version: v1.2.0
Date: 2026-01-30

### Added
- Viewer v1.2 Dashboard Shell Redesign (DataDash V1-style)
  - Queue-centric sidebar navigation: To Do, Needs Review, Flagged, Blocked, Finalized
  - Dynamic queue count badges that update based on contract status
  - Session management section: Data Sources, Evidence Status, Reset Session
  - Role selector: Analyst (default), Reviewer, Admin
  - Tools section: Patch Studio navigation
  - Data Sources Drawer: Right-side slide-over replacing centered modal
  - Record Drawer: Right-side slide-over for contract details with Previous/Next navigation
  - Topbar with Load Data button, session status chip, and quick actions

### Changed
- Replaced centered hero layout with sidebar + topbar + main workbench design
- Sidebar width: 280px fixed, with collapsible sections
- Modal → Drawer: Data Sources now slides in from right instead of centered overlay
- Removed legacy Operator role (auto-converted to Analyst on load)
- Contract table rows now open Record Drawer with full details, issues, and actions

### Technical Details
- No new dependencies or build step
- Single-file vanilla HTML+JS maintained
- All existing determinism guarantees unchanged
- Legacy 'operator' mode auto-converts to 'analyst'

---

## Version: v1.1.1
Date: 2026-01-30

### Added
- Viewer v1.1.1 Loader Simulation for Upload-First UX
  - Three input modes in Load Data modal: Paste JSON, Drag-and-drop file, Path hint (read-only label)
  - Session status chip in top toolbar: NOT LOADED / LOADED / FALLBACK
  - Session metadata display: source type (paste/drop/example), loaded timestamp
  - LocalStorage persistence with opt-in "Remember in this browser" toggle
  - Reset Session action that clears artifacts but preserves patch draft
  - Triage page shows active artifact source: memory(paste/drop) vs fallback(example) vs none

### Technical Details
- Product renamed to "Orchestrate OS" (internal title update)
- No external dependencies added
- Copy-to-clipboard only (no file writes)
- Deterministic sorting unchanged

---

## Version: v1.1.0
Date: 2026-01-30

### Added
- Viewer v1.1 Upload-First Flow + Modal Wizards
  - Welcome Hero: Clear "Load Data" CTA when no data is loaded
  - Data Source Modal: Select artifact path from presets or custom path
  - Ruleset Modal: Configure base config (Truth) + patch (Proposed) paths
  - Compare Modal: Load comparison artifact for delta visualization
  - Run Modal: Copy validation/preview/smoke commands to terminal
  - Triage-first landing: After loading data, user lands on Triage page by default
  - Review page hidden behind Reviewer mode toggle
  - "Build Patch" button in Workbench for contextual patching

### Changed
- Removed Run page from navigation (commands now in Run modal)
- Default route changed from #/run to #/triage
- Top toolbar appears after data is loaded with Load Data, Ruleset, Compare, Run buttons

### Technical Details
- No new dependencies or build step
- All existing determinism guarantees unchanged
- Copy-to-clipboard only (no file writes from browser)

---

## Version: v1.0.0
Date: 2026-01-30

### Added
- Viewer v1.0 Multi-Page Navigation + Mode Toggle
  - Left-nav sidebar with 4 pages: Run, Triage, Patch Studio, Review
  - Hash-based routing (#/run, #/triage, #/patch, #/review)
  - Mode toggle: Operator, Reviewer, Analyst (persisted to localStorage)
  - Run page: Toolbar, dataset paths, status summary, Stream Model as collapsible About
  - Triage page: Summary cards, filters, queues, workbench drilldown
  - Patch Studio page: Preflight Gate, Patch Draft Builder, copy outputs
  - Review page: Config+Patch Inspector, Session Loader (Comparison Mode), Evidence summary
  - Why: Improve navigation and focus by separating workflows into dedicated pages.

### Technical Details
- All existing features preserved (no regressions)
- Hash-based routing for SPA-like navigation within single HTML file
- Mode toggle changes visible emphasis (placeholder for future mode-specific visibility)
- Storage keys updated to v10

---

## Version: v0.9.0
Date: 2026-01-30

### Added
- Viewer v0.9 Session + Stream Model (Conceptual Bridge)
  - Session Timeline Panel: Models ordered sessions (ingest waves) as UI-only JSON
  - Record State Model: CONSOLIDATED | PARTIAL | WAITING | BLOCKED derived from issues
  - Never-Stop Flow Visualization: Explains open faucet concept for continuous processing
  - Reconsolidation Rules Table: Shows how partial records upgrade to consolidated
  - Copy Stream Semantics Markdown: One-click PR-ready explanation export
  - Why: Lay semantic groundwork for future streaming without runtime execution.
- docs/14_stream_semantics.md: Governance-only explanation of stream model

### Technical Details
- Record state derived deterministically from issue severity and type
- Session simulation based on loaded artifact data
- All computations performed offline in the browser
- No actual streaming, async processing, or runtime changes

---

## Version: v0.8.0
Date: 2026-01-30

### Added
- Viewer v0.8 Config + Patch Inspector (Ruleset Delta Viewer)
  - Ruleset Loader Panel: Collapsible UI to load base config + patch files
  - Patch Summary: Displays base.version, patch.base_version, author, rationale, changes_count
  - Version Match Chip: RED mismatch indicator when base_version differs
  - Changes[] Table: Deterministic table of patch changes with action, target, rule_id, when, then, severity
  - Ruleset Delta Counts: Added/Deprecated counts per target (salesforce/qa/resolver)
  - Copy Ruleset Delta Markdown: One-click export of PR-ready semantic delta description
  - Preflight Integration: Loaded config versions auto-populate Preflight Base Version Check
  - Why: Enable operators to inspect semantic ruleset changes before submitting PRs.

### Technical Details
- Deterministic change sorting: target asc, action asc, rule_id asc (nulls last), when.sheet, when.field, severity order, then fields
- All computations performed offline in the browser, no network requests
- Base + patch loaded via relative paths, no file uploads

---

## Version: v0.7.0
Date: 2026-01-30

### Added
- Viewer v0.7 Comparison Mode
  - Session Loader UI: Collapsible panel with primary and comparison artifact path inputs
  - Delta Summary Cards: Visual display of contract status changes and row-level deltas
  - Row Change Indicators: Green (added), orange (changed), red strikethrough (removed) for tables
  - Copy Delta Summary button: Export delta statistics as Markdown
  - Why: Enable operators to analyze semantic changes between artifact versions without external tools.

### Technical Details
- Join identity for change detection: `contract_key|file_url|file_name` (extended for issues/actions)
- Content hash using JSON.stringify with sorted keys for deterministic comparison
- All delta computations performed offline in the browser, no network requests

---

## Version: v0.1.0
Date: 2026-01-29

### Added
- Semantic Control Board governance documents (SCOPE_control_plane.md, CONTROL_BOARD_ARCHITECTURE.md, RULE_LIFECYCLE.md, INTERFACES.md, TRUTH_SNAPSHOT.md, CONFLICT_RESOLUTION.md, REVIEW_CHECKLIST.md, examples/README.md)
  - Why: Establish a single, auditable source of semantic truth and clear operating boundaries.
- Canonical join strategy (contract_key → file_url → file_name)
  - Why: Ensure deterministic linking across stages and prevent silent data drift.
- Determinism guarantee for previews (offline only)
  - Why: Make outcomes reproducible and reviewable without runtime dependencies or network calls.
- Operator-first index and templates (INDEX.md, rule templates, config templates)
  - Why: Streamline authoring and review, reduce ambiguity, and support consistent change control.

### Changed
- Consolidated repository as a governance-only control plane (no runtime code, no APIs, no credentials)
  - Why: Maintain a stable, reviewable semantic authority separate from execution environments.
- Local preview harness: join-triplet grouping fix (contract_key → file_url → file_name) for status aggregation and issue/action attribution
  - Why: Prevent mis-aggregation when contract_key is missing; ensure consistency across all joins.
- Local preview harness: join-failure diagnostic (blocking) when a THEN targets a missing target row (e.g., catalog)
  - Why: Surface unsafe application of rules and force BLOCKED status deterministically.
- Validator: strict base_version enforcement for patches (patch.base_version must equal base.version)
  - Why: Prevent drift and ensure patches apply to the intended base semantics.

### Deprecated
- None in this initial version
  - Why: First release of governance materials; no prior artifacts to deprecate.

---

## Version: v0.1.1
Date: 2026-01-29

### Added
- docs/07_replit_mcp.md and scripts/mcp_link_gen.py (deterministic ENCODED/LINK/BADGE_MARKDOWN output)
  - Why: Enable safe, reproducible MCP setup in Replit without secrets.
- scripts/replit_smoke.sh strict diff gate (with `--allow-diff` override)
  - Why: Provide a clear pass/fail operator signal and reproducible verification.

### Changed
- README.md and docs/INDEX.md updated to include Replit MCP and smoke flow
  - Why: Improve discoverability and reduce operator onboarding time.

### Verification
- Replit golden run verified — see docs/replit_baseline.md (records date/time, environment, and SHA256 of out/sf_packet.preview.json).

### Deprecated
- None
  - Why: Non-breaking governance-surface enhancements only.

---

## Version: v0.1.2
Date: 2026-01-30

### Changed
- Determinism hardening in preview outputs: explicit array sorting by join triplet (contract_key → file_url → file_name) and normalized key ordering for diffing.
  - Why: Eliminate incidental ordering diffs; ensure stable, audit-friendly previews.
- Documentation updates:
  - TRUTH_SNAPSHOT: clarified authoritative vs illustrative files and config-driven semantics.
  - replit_baseline: added narrative of determinism fix and authority of smoke tests over editor diagnostics.

### Notes
- No semantic rule changes. Configuration meaning is unchanged; this release only enforces ordering/normalization for deterministic previews.

### Required Operator Action
- Treat v0.1.2 as the locked baseline. Future changes require a version bump and strict smoke pass (baseline and, when applicable, edge-case packs).

---

## Version: v0.1.3 (DRAFT)
Date: 2026-01-30

### Added
- Patch: config/config_pack.v0.1.3.patch.json (SF_R2_ARTIST_REQUIRES_ARTIST_NAME — warning completeness rule)

### Changed
- examples/expected_outputs/sf_packet.example.json updated to reflect new rule (artist row Needs Review)

### Why
- Low-risk, demonstrable rule aligned with subtype expectations. Determinism unaffected.

### Smoke Evidence
- Baseline smoke should pass with updated expected output.

---

## Meta: Product Rename (2026-01-30)
- Changed: Product name to “Orchestrate OS.”
- Why: Unify naming; semantics unchanged. Historical aliases (Kiwi, Control Board, Kiwi Semantic Control Board) remain as searchable references.