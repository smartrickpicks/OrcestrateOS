# CLAUDE.md — Orchestrate OS

> AI assistant guide for the Orchestrate OS codebase. Read this before making changes.

---

## What Is This Project?

**Orchestrate OS** (formerly "Kiwi," "Control Board," "Kiwi Semantic Control Board") is a governance-only semantic control plane for music industry contract data. It allows record labels to load, review, correct, and approve contract workbooks before data flows into downstream systems (Salesforce).

Core philosophy:
- **Offline-first, deterministic** — same inputs always produce same outputs
- **No AI in the governance path** — all decisions are explicit, traceable, auditable
- **Evidence-gated** — no patch moves forward without source document evidence
- **Append-only audit** — every write emits an audit event; no silent mutations

Legacy aliases still appearing in docs/code: `kiwi`, `control_board`, `single_row_review` (internal code token for what users see as "Record Inspection").

---

## Repository Structure

```
OrcestrateOS/
├── server/               # FastAPI backend (Python 3.11)
│   ├── pdf_proxy.py      # App entry point — mounts all routers
│   ├── api_v25.py        # Shared envelope helpers, base router
│   ├── db.py             # psycopg2 connection pool (DATABASE_URL)
│   ├── auth.py           # JWT decode/verify helpers
│   ├── jwt_utils.py      # JWT creation utilities
│   ├── feature_flags.py  # Env-var-based feature flags
│   ├── migrate.py        # Migration runner (runs on startup)
│   ├── role_scope.py     # RBAC helpers
│   ├── suggestion_engine.py  # Heuristic column-header suggestion engine
│   ├── preflight_engine.py   # PDF page classification engine
│   ├── contract_health_runtime.py  # Contract health scoring
│   ├── ulid.py           # ULID generation
│   ├── routes/           # One file per API resource
│   │   ├── workspaces.py, batches.py, patches.py, contracts.py
│   │   ├── documents.py, accounts.py, annotations.py
│   │   ├── evidence_packs.py, rfis.py, triage_items.py
│   │   ├── signals.py, selection_captures.py, audit_events.py
│   │   ├── sse_stream.py, auth_google.py, members.py
│   │   ├── drive.py, sessions.py, reader_nodes.py
│   │   ├── anchors.py, corrections.py, batch_health.py
│   │   ├── ocr_escalations.py, suggestions.py, glossary.py
│   │   ├── preflight.py, operations_queue.py
│   │   └── __init__.py
│   ├── migrations/       # Sequential SQL migration files (001–013)
│   └── resolvers/
│       └── salesforce.py # Salesforce entity resolution stub
│
├── ui/                   # Frontend (vanilla JavaScript, no framework)
│   ├── viewer/
│   │   ├── index.html    # Main app — single large file, 55+ AppModules
│   │   ├── theme.css     # Dark/light mode color tokens (single source of truth)
│   │   ├── drive-callback.html  # Google Drive OAuth callback
│   │   └── test-data/    # Test fixtures
│   ├── landing/
│   │   └── index.html    # Google Sign-In landing page
│   └── demo/             # Sandbox demo mode assets
│
├── local_runner/         # Offline governance harness (stdlib Python, no network)
│   ├── validate_config.py  # Validates base + patch config files
│   └── run_local.py      # Generates deterministic preview output
│
├── config/               # Config pack artifacts and docs
│   ├── config_pack.base.json          # Truth Config (authoritative semantics)
│   ├── config_pack.example.patch.json # Example patch format
│   ├── contract_health_bands.json     # Health scoring thresholds
│   ├── document_types.json            # Document classification definitions
│   ├── id_extraction_rules.json       # URL/ID canonicalization rules
│   ├── section_guidance.json          # Field section guidance
│   ├── knowledge_links.json           # Glossary term knowledge links
│   └── docs/             # Extensive spec/PRD documentation
│       ├── INDEX.md       # Primary navigation — start here
│       ├── 00_system_overview.md through 06_how_to_add_rules.md
│       ├── api/           # OpenAPI spec, API canonical spec
│       ├── architecture/  # AppModules map, catalog, index
│       ├── decisions/     # Locked design decisions
│       ├── features/      # Feature specs
│       ├── handoff/       # Version handoff docs (V25x series)
│       └── ...
│
├── scripts/              # Shell and Python utilities
│   ├── replit_smoke.sh   # Strict smoke test (exit 1 on diff)
│   ├── serve_viewer.sh   # Serve the UI viewer locally
│   └── materialize_repo.py  # Repo snapshot tool (offline only)
│
├── tests/                # pytest test suite
│   ├── test_suggestion_engine.py
│   └── test_contract_health_calibration_runtime.py
│
├── examples/             # Synthetic datasets and expected outputs
│   ├── standardized_dataset.example.json
│   ├── standardized_dataset.edge_cases.json
│   └── expected_outputs/
│       ├── sf_packet.example.json    # Baseline expected
│       └── sf_packet.edge_cases.json # Edge case expected
│
├── rules/                # Operator-facing rule authoring templates
│   ├── salesforce_rules.txt
│   ├── qa_rules.txt
│   └── resolver_rules.txt
│
├── models/               # Trained ML model artifacts
│   ├── contract_health_calibrator.joblib
│   └── contract_health_calibrator.json
│
├── out/                  # Generated preview output (gitignored)
│   └── sf_packet.preview.json
│
├── supabase/             # Supabase configuration
├── assets/               # Brand assets (brand/, functions/)
├── analysis/             # Analysis documents
├── .replit               # Replit run config (entry point + workflows)
├── requirements.txt      # Python dependencies
├── package.json          # Node deps (@redocly/cli for OpenAPI validation)
└── replit.md             # Full system description (canonical reference)
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend language | Python 3.11 |
| Backend framework | FastAPI + uvicorn |
| Database | PostgreSQL (Neon-hosted), psycopg2 driver |
| Authentication | Google OAuth (OIDC) + HS256 JWT (24h expiry) |
| PDF processing | PyMuPDF (fitz) |
| Excel I/O | openpyxl (server), SheetJS/XLSX (browser) |
| Fuzzy matching | rapidfuzz |
| Frontend | Vanilla JavaScript (ES5-compatible), no framework |
| Frontend storage | IndexedDB for workbook session cache |
| SSE | sse-starlette (server-sent events) |
| Google APIs | google-auth, google-auth-oauthlib, google-api-python-client |
| Testing | pytest |
| Node tools | @redocly/cli (OpenAPI validation) |
| Platform | Replit (Nix-based, Python 3.11 + Node 22 + PostgreSQL 16) |

---

## Running the Project

### Start the Server (Primary Entry Point)

```bash
python -m uvicorn server.pdf_proxy:app --host 0.0.0.0 --port 5000
```

The `pdf_proxy.py` module is the real app entry point — it mounts all 28+ route routers and runs DB migrations on startup.

### Environment Variables Required

| Variable | Purpose | Notes |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | Required for all DB operations |
| `JWT_SECRET` | HS256 JWT signing key | Dev default set in `.replit` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Required for production login |
| `DRIVE_ROOT_FOLDER_ID` | Google Drive root folder | Set in `.replit` for dev |
| `EVIDENCE_INSPECTOR_V251` | Feature flag | `true` in dev |
| `PREFLIGHT_GATE_SYNC` | Feature flag | `true` in dev |
| `OPS_VIEW_DB_READ` | Feature flag | DB-backed ops queue reads |
| `OPS_VIEW_DB_WRITE` | Feature flag | DB-backed ops queue writes |
| `PDF_PROXY_ALLOWED_HOSTS` | Comma-separated allowed PDF hosts | Default: S3 bucket |

### Offline Governance Harness

```bash
# 1. Validate config
python3 local_runner/validate_config.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json

# 2. Generate deterministic preview
python3 local_runner/run_local.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json \
  --standardized examples/standardized_dataset.example.json \
  --out out/sf_packet.preview.json

# 3. Smoke tests (strict diff — fails on any output change)
bash scripts/replit_smoke.sh            # baseline
bash scripts/replit_smoke.sh --edge     # edge cases
bash scripts/replit_smoke.sh --allow-diff  # non-blocking diff view
```

### Run Tests

```bash
pytest tests/
```

---

## Database Migrations

Migrations run automatically on server startup via `server/migrate.py`. They are sequential SQL files in `server/migrations/`:

```
001_core_tables.sql
002_seed_fixtures.sql
003_auth_google_oauth.sql
004_drive_and_sessions.sql
005_evidence_inspector_v251.sql
006_anchors_selected_text_hash.sql
007_rfi_custody_owner.sql
008_suggested_fields.sql
009_alias_versioning.sql
010_drive_save_settings.sql
011_member_drive_folders.sql
012_ops_view_v254.sql
013_drive_batch_source.sql
```

**Convention:** Add new migrations as `NNN_descriptive_name.sql` with the next sequential number. Never modify existing migrations — always add new ones.

---

## API Design

**Base URL:** `/api/v2.5/`

### ID Format

All primary keys use prefixed ULIDs: `{prefix}_{ulid}`

| Prefix | Resource |
|---|---|
| `ws_` | Workspace |
| `bat_` | Batch |
| `acc_` | Account |
| `ctr_` | Contract |
| `doc_` | Document |
| `pat_` | Patch |
| `evp_` | Evidence Pack |
| `sig_` | Signal |
| `tri_` | Triage Item |
| `aud_` | Audit Event |
| `rfi_` | RFI |
| `ann_` | Annotation |
| `sel_` | Selection Capture |
| `usr_` | User |

### Response Envelope

All responses use a consistent envelope:

```json
// Success (single resource)
{ "data": { ... }, "meta": { "request_id": "req_...", "timestamp": "..." } }

// Success (collection)
{ "data": [ ... ], "meta": { "cursor": "...", "total": N } }

// Error
{ "error": { "code": "ERROR_CODE", "message": "..." } }
```

### Key Conventions

- **PATCH** for status transitions and partial updates
- **POST** for resource creation
- **Optimistic concurrency:** include `version` field on PATCH; server returns `409 STALE_VERSION` on conflict
- **No self-approval:** server enforces that the approver ≠ submitter
- **Audit events:** every mutating endpoint emits an audit event automatically
- **Workspace isolation:** all resources are scoped to a `workspace_id`

---

## Feature Flags

Feature flags are environment variable-based, read via `server/feature_flags.py`:

```python
from server.feature_flags import is_enabled, require_preflight, is_ops_view_db_read

# Check a flag
if is_enabled("MY_FEATURE_FLAG"):
    ...

# Gate a route (returns 404 JSONResponse if disabled)
gate = require_preflight()
if gate:
    return gate
```

Flag values: `true`, `1`, `yes`, `on` → enabled. Cached in `_FLAG_CACHE` after first read; call `clear_cache()` in tests.

---

## Frontend Architecture

The UI is a single-file vanilla JavaScript application at `ui/viewer/index.html`. No build step, no framework.

### AppModules System

The frontend uses a module registry called `window.AppModules` with 55+ modules organized into phases:

- **Engines** (`AppModules.Engines.*`): state management
- **Components** (`AppModules.Components.*`): UI rendering

Phases C, D1–D15 cover: Grid, Record Inspector, PDF Viewer, Admin Panel, Audit Timeline, DataSource/Import, System Pass, Contract Health, Data Quality, Batch Merge, Grid Context Menu, Patch Studio, Contract Index, Export Engine, Rollback/Undo.

Reference: `config/docs/architecture/appmodules-catalog.md` (full module catalog), `config/docs/architecture/appmodules-map.md` (Mermaid dependency graph).

**ES5 compliance required** — the viewer must work in ES5-compatible environments. No arrow functions, template literals, destructuring, or other ES6+ in the core viewer code.

### Theme System

`ui/viewer/theme.css` is the **single source of truth** for all color tokens. Light mode uses `:root` variables; dark mode uses `html[data-theme="dark"]`. Never hardcode colors in JS or inline styles — always use CSS custom properties.

### Routing

The app uses hash-based routing: `#page-triage`, `#/verifier-org` (redirects to `#/triage`), etc. URL state sync via query params: `#/triage?status=X&type=Y&batch=Z`.

### Storage

- **IndexedDB**: workbook session cache (large payloads)
- **localStorage**: UI preferences (dark mode, sidebar collapsed), small state only
- **PostgreSQL**: all durable governance data via API

---

## Roles and Access Control

| Role | Capabilities |
|---|---|
| **Analyst** | Load workbooks, triage records, draft patches, attach evidence, submit for verification |
| **Verifier** | Review patches, test corrections, approve/reject/raise RFIs |
| **Admin** | Promote to canonical truth, manage workspace members, configure workspace |
| **Architect** | System-level calibration, Truth Config clean-room access |

**RBAC enforcement:** `server/role_scope.py` + `server/auth.py`. All routes check role on authenticated requests. Inactive users are denied on every request.

**Role simulation:** Admin/Architect can simulate Analyst or Verifier roles in sandbox mode. Simulated actions are tagged in audit events.

---

## Governance Model

### Four Gates (non-negotiable)

1. **Evidence Gate** — No patch submits without attached source document evidence
2. **Naming Gate** — Exported artifacts follow `{batch_id}-{actor}-{status}-{timestamp}.xlsx`
3. **Validation Gate** — Schema validation, duplicate account checks, address completeness
4. **Role Authority Gate** — No self-approval; Verifier approves → Admin promotes

### Patch Lifecycle (12 statuses)

Patches move through states: Draft → Submitted → Under Review → Clarification Requested → Resubmitted → Verifier Approved / Rejected → Admin Approved / Rejected → Promoted / Rolled Back. See `config/docs/api/API_SPEC_V2_5_CANONICAL.md` for the full transition matrix.

### Terminology (canonical — do not deviate)

**Use these terms:**
- Data Source (not "Load Data")
- All Data Grid
- Record Inspection (internal code: `single_row_review`)
- Verifier Review
- Admin Approval
- Submit Patch Request (not "Apply Patch")
- Evidence Pack blocks: Observation, Expected, Justification, Repro
- Triage (not "Queue" in user-facing labels)

**Forbidden in user-facing UI:**
- "Load Data"
- "Apply Patch"
- "Reviewer Hub"
- "Queue" as a navigation/button label

---

## Key Domain Concepts

- **Config Pack**: `base.json` (authoritative truth) + `patch.json` (proposed changes). Strict version matching enforced.
- **Workspace**: Top-level isolation unit. All data scoped to `workspace_id`.
- **Batch**: A collection of contract workbooks imported together.
- **Contract**: One record label contract = one channel of events.
- **Signal**: Deterministic cell-level flag generated by semantic rules (WHEN/THEN pattern).
- **Patch Request**: A proposed correction to contract data, gated by evidence and role approval.
- **RFI (Request for Information)**: Verifier asks Analyst to clarify something.
- **Evidence Pack**: Source document evidence attached to a patch (PDF text anchors).
- **Annotation Layer**: DB-backed record of verifier actions (patches, RFIs, corrections).
- **SystemPass**: Mechanism for deterministic (non-human) batch changes.
- **UndoManager**: Session-scoped draft edit undo (local only, not governed).
- **RollbackEngine**: Governed rollback creating append-only artifacts.

---

## Adding a New API Route

1. Create `server/routes/my_resource.py` with a FastAPI `APIRouter`
2. Follow the pattern: use `server/db.py` for DB access, `server/auth.py` for auth, `server/api_v25.py` for error envelopes
3. Import and mount in `server/pdf_proxy.py`:
   ```python
   from server.routes.my_resource import router as my_resource_router
   app.include_router(my_resource_router, prefix="/api/v2.5")
   ```
4. If new DB tables needed, add `NNN_descriptive_name.sql` to `server/migrations/`
5. Emit audit events on all mutating operations

---

## Adding a New Feature Flag

In `server/feature_flags.py`:
```python
MY_NEW_FLAG = "MY_NEW_FLAG"

def require_my_flag():
    if not is_enabled(MY_NEW_FLAG):
        return JSONResponse(status_code=404, content=error_envelope(
            "FEATURE_DISABLED", "Set MY_NEW_FLAG=true to activate."
        ))
    return None
```

Set the env var in `.replit` under `[userenv.shared]` for development.

---

## Testing Conventions

- Tests live in `tests/`
- Run with `pytest tests/`
- Use `server.feature_flags.clear_cache()` in test setup if testing flag-gated paths
- The smoke tests (`scripts/replit_smoke.sh`) are the arbiter of output correctness for the local runner — update `examples/expected_outputs/` and `CHANGELOG.md` when expected output changes intentionally

---

## Important Files to Know

| File | Purpose |
|---|---|
| `server/pdf_proxy.py` | App entry point, router mounting, startup hooks |
| `server/api_v25.py` | Shared response envelopes, error helpers |
| `server/feature_flags.py` | All feature flag definitions |
| `server/db.py` | DB connection pool |
| `server/migrate.py` | Migration runner |
| `ui/viewer/index.html` | Entire frontend application |
| `ui/viewer/theme.css` | All CSS color tokens |
| `config/config_pack.base.json` | Authoritative semantic truth config |
| `config/docs/INDEX.md` | Documentation navigation hub |
| `config/docs/00_system_overview.md` | System overview for new contributors |
| `config/docs/api/API_SPEC_V2_5_CANONICAL.md` | Full API specification |
| `config/docs/architecture/appmodules-catalog.md` | Frontend module catalog |
| `replit.md` | Comprehensive system description (canonical reference) |
| `CHANGELOG.md` | Version history |

---

## What NOT to Do

- Do not add AI/LLM calls to the governance path — it must remain deterministic
- Do not modify existing migration SQL files — add new ones instead
- Do not hardcode colors in the viewer — use `theme.css` CSS custom properties
- Do not use ES6+ syntax in `ui/viewer/index.html` — ES5 compatibility required
- Do not store large payloads in localStorage — use IndexedDB
- Do not allow self-approval anywhere in the patch lifecycle
- Do not make network calls from `local_runner/` — it must be offline-only
- Do not deviate from canonical terminology (see Terminology section above)
- Do not skip audit event emission on mutating API routes
