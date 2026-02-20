# V256 Contract Reconstruction V1 (Ostereo Pilot)

Status: Draft implementation spec  
Scope: Admin sandbox only  
Pilot legal entity: Ostereo

## Purpose
Use Contract Generator as a preflight reconstruction path for encoding-/OCR-corrupted contracts, so ingestion and generation operate on the same canonical schema and audit model.

Key principles:
- JSON-first: canonical contract representation is structured JSON, not the original PDF/image.
- Template-governed: reconstruction uses Ostereo template packs only (no LLMs in V1).
- Audit-strict: every reconstructed clause has immutable lineage back to:
  - Source artifact (even if corrupted),
  - Template version,
  - Reviewer decisions.

---

## V1 Routing Policy

### 1. Health Score Routing
1. Green
   - Normal ingestion path.
   - Optional `Generate Copy` for parity export (no additional review required by default).
2. Yellow
   - Allow `Accept Risk` (legacy behavior) or `Generate Copy`.
   - If `Generate Copy` is chosen:
     - Reviewer must compare source snippets vs generated clauses before marking reconstruction complete.
     - High-risk clauses must be explicitly reviewed (see Clause Safety Policy).
3. Red
   - Block `Accept Risk`.
   - Require `Generate Copy` flow.
   - Contract remains reconstruction-driven until:
     - Required fields are populated, and
     - All required reviews are complete (including red-case escalation).

### 2. Hard/Soft Rules (Pilot Defaults)
- Green
  - Auto-allow reconstruction of low-risk boilerplate.
  - High-risk clauses: review recommended but not strictly enforced in V1.
- Yellow
  - High-risk reconstructed clauses: required human review before marking contract as reconstruction-complete.
- Red
  - No contract can be promoted as `reconstruction_complete` without:
    - Legal/lead override on the contract as a whole, and
    - Per-clause decisions on high-risk content.

---

## Preflight UX Changes (V1)

### 1. Replace OCR Escalation with `Generate Copy`
Replace existing `Escalate OCR` CTAs with `Generate Copy` in:
- Document preflight gate panel
- Preflight simulator modal
- Mojibake gate banner
- Preflight Test Lab footer action

Behavior:
- Yellow:
  - Show `Accept Risk` and `Generate Copy`.
- Red:
  - Hide/disable `Accept Risk`.
  - Show only `Generate Copy` as valid resolution.

### 2. `Generate Copy` Behavior
When user clicks `Generate Copy`:
1. Persist preflight action as `generate_copy` via `/api/preflight/action` with:
   - `action_taken: "generate_copy"`
   - `actor`, `timestamp`
   - `health_score` (green/yellow/red)
   - `source_document_id` / SRR context
2. Open Contract Generator page with:
   - Attempt to seed current sheet/row context from SRR state:
     - Ostereo legal entity
     - Contract type (if known)
     - Relevant SF objects (Opportunity, Account, Schedule, etc.)
   - If context is complete:
     - Auto-run generator (no extra click)
   - If context is incomplete:
     - Land user on Contract Generator with missing fields highlighted (preflight gating in that UI).
3. Update preflight gating logic:
   - Treat `generate_copy` as a valid resolution path for yellow and red documents:
     - Yellow: allow progression once reconstruction is generated and required reviews pass.
     - Red: allow progression only after reconstruction and red-case override conditions are met.

### 3. Backward Compatibility
- `/api/preflight/action` must:
  - Accept `generate_copy` as a new enum value.
  - Continue accepting legacy `accept_risk` and `escalate_ocr` payloads.
- Legacy `escalate_ocr`:
  - Tolerated in payloads but UI no longer surfaces that option in V256 preflight screens.

---

## Data and Governance Behavior
1. Canonical record
   - Remains JSON-first.
   - Contract Generator produces canonical JSON conforming to the same schema used for:
     - Normal ingestion
     - Downstream generation
2. Exports
   - Generated Markdown/PDF are exports only, not source of truth.
   - Export metadata must include:
     - `generated_from: "reconstructed_json"`
     - `environment: "admin_sandbox"`
     - `pilot: "Ostereo_V1"`
3. Auditability
   - Every reconstruction-related action is recorded:
     - `action_taken` (e.g., `generate_copy`, `accept_risk`, `override_red`)
     - `actor`
     - `timestamp`
     - `health_score_at_action`
   - Clause-level lineage is append-only.
4. Preflight gating
   - Existing preflight gating logic is extended:
     - `generate_copy` is treated as a valid resolution for yellow and red health scores.
   - Contracts cannot exit reconstruction state until:
     - All required clause reviews are complete, and
     - Any required red overrides are recorded.

---

## Clause Safety Policy (Ostereo Pilot, ROVO-aligned)

### 1. High-Risk Clause Families (Mandatory Review When Reconstructed)
For Ostereo V1, the following clause families are high-risk and must be reviewed when reconstructed from templates:
- Liability / indemnity
- Limitation of liability and caps
- Governing law / jurisdiction / dispute resolution
- IP ownership, license grant, assignment of rights
- Term and termination (including renewal, termination for convenience)
- Financial obligations:
  - Payment terms
  - Recoupment, royalty rates, advances
  - Audit rights tied to financials

Controls:
- Template metadata (`clause_template` level) must include:
  - `risk_family` (e.g., `"liability"`, `"ip"`, `"financial"`)
  - `requires_legal_review_if_reconstructed: true|false`
- Orchestration:
  - If `requires_legal_review_if_reconstructed = true` and clause is reconstructed:
    - UI must show clause as `Needs Review`.
    - Contract cannot be marked `reconstruction_complete` until reviewer sets decision:
      - `ACCEPTED` / `MODIFIED_AND_ACCEPTED` / `REJECTED`.

### 2. Unreadable High-Risk Text
If high-risk source text is partially or mostly unreadable:
- System still allows reconstruction using canonical Ostereo template, but:
  - Reconstructed clause is flagged as `DRAFT_ONLY` until reviewer decision.
  - Reviewer must see:
    - Original fragment (even if corrupted)
    - OCR confidence metrics
    - Template version used
- For severely unreadable cases (red-like OCR in high-risk blocks), apply Red escalation policy.

### 3. Low-Risk / Boilerplate Clauses
Examples: headings, table of contents, standard definitions, notice mechanics if parameterized from readable fields.
- May be auto-reconstructed and auto-accepted in:
  - Green docs
  - Yellow docs (recommended: still visible in review UI)
- Template metadata:
  - `risk_family: "boilerplate"` and `requires_legal_review_if_reconstructed: false`

### 4. No Silent Entity Fallback
- If an Ostereo-specific clause template is missing:
  - System must not silently fall back to global or CMG-level templates.
- Acceptable fallback path:
  - Clause marked `NO_ENTITY_TEMPLATE_AVAILABLE`.
  - Reviewer can:
    - Manually select global/alternate template only for low-risk clauses.
    - Provide mandatory reviewer note, e.g.:
      - "Using CMG global notices clause as placeholder; Ostereo variant missing. Do not treat as executed language."
- All such clauses must carry:
  - `entity_mismatch_fallback: true`
  - `fallback_source_entity: "CMG_Global"` (or equivalent)

---

## Reviewer Protocol (Reconstructed Clauses)

### 1. Side-by-Side Evidence Requirements
When reviewing a reconstructed clause, UI must display:
- Source side:
  - Original corrupted excerpt (image or text)
  - OCR text (if any)
  - OCR confidence score for that block
  - Page and coordinate (if available)
- Template side:
  - Template pack ID + version
  - Clause template ID
  - Risk family and review flag (`requires_legal_review_if_reconstructed`)
- Output side:
  - Reconstructed clause text (from canonical JSON)
  - Field parameterization (e.g., amounts, territories)

Reviewer actions per clause:
- `ACCEPTED`
- `MODIFIED_AND_ACCEPTED` (with inline edits)
- `REJECTED` / `CANNOT_RECONSTRUCT`

Each decision writes an audit record with:
- `clause_id`
- `decision`
- `reviewer_id`
- `reviewed_at`
- Optional `review_notes`

### 2. Red-Case and Severe Corruption Escalation
Escalation criteria:
- High-risk clause and:
  - OCR confidence for that block `< 0.80`, or
  - More than 3 contiguous lines unreadable, or
  - Key tokens (numbers, named parties, jurisdiction names) missing.

When criteria hit:
- System sets `clause_escalation_state: "NEEDS_LEGAL_ESCALATION"`.
- Contract cannot be globally marked `reconstruction_complete` until designated Ostereo legal/lead reviewer:
  - Either approves using template as operational substitute with explicit note:
    - "Treat as operational text, not verified original."
  - Or marks `SOURCE_REQUIRED` (reconstruction not acceptable).

For red contracts overall:
- At least one Ostereo legal/lead user must set:
  - `contract_override: "red_accepted_for_reconstruction"` with reason.

---

## Compliance, Retention, and Lineage

### 1. Retention (Pilot Default)
Until a formal schedule exists, follow "retain with the contract" for all related artifacts:
- Original corrupted files (PDF/images):
  - Retain as long as contract record exists in admin sandbox.
- Reconstructed JSON:
  - Stored as canonical contract record (sandbox tier).
- Exports (Markdown/PDF):
  - Regenerable; may follow same retention, or shorter once policy is defined.
- Review and annotation logs:
  - Retain alongside reconstructed JSON (no early deletion in pilot).

### 2. Immutable Clause Lineage
For each reconstructed clause, persist:
- `clause_id` (stable within contract)
- `source_document_id`
- `source_location` (page, coordinates or OCR segment refs)
- `template_pack_id`
- `template_pack_version`
- `reconstruction_timestamp`
- `reconstructed_by` (system or user)
- `review_decision`
- `reviewer_id`, `reviewed_at`
- Optional `review_notes`
- Optional `hash_original_fragment`, `hash_reconstructed_clause` (tamper-evidence)

Storage must be append-only; changes add new records, old ones remain.

---

## Risk Controls and Quality Gates

### 1. Health Score Hard-Blockers
- Green
  - No additional hard blockers beyond preflight rules; allow reconstruction as quality-of-life feature.
- Yellow
  - Hard-block contract promotion if:
    - Any high-risk reconstructed clause lacks review decision, or
    - Overall clause preflight finds missing required fields.
- Red
  - Hard-block `Accept Risk`.
  - Hard-block promotion until:
    - All reconstructed clauses have review decisions, and
    - At least one Ostereo legal/lead has set red override:
      - `red_override: true`
      - `red_override_by`, `red_override_at`
      - `red_override_reason`

### 2. Downstream Promotion Gates
Before reconstructed contract can:
- Leave admin sandbox, or
- Be used by downstream automation (even in sandbox),
require:
1. All required clause reviews are `ACCEPTED` / `MODIFIED_AND_ACCEPTED`.
2. No unresolved `NEEDS_LEGAL_ESCALATION` clauses remain.
3. No hard preflight errors (e.g., missing parties, invalid governance fields).
4. Contract status explicitly set to `reconstruction_complete` by authorized reviewer.

For V1 pilot:
- Add environment guard:
  - Contracts cannot be pushed to production integration endpoints.
  - All V1 activity remains sandbox-only.

---

## Acceptance Criteria
1. Preflight UI
   - Yellow preflight shows `Generate Copy` and allows progression when selected.
   - Red preflight blocks `Accept Risk` and requires `Generate Copy`.
2. Contract Generator Integration
   - Clicking `Generate Copy` opens Contract Generator and attempts to seed active SRR/row context.
   - When context is complete, generator auto-runs and produces canonical JSON.
3. API / Preflight Actions
   - `/api/preflight/action` accepts `generate_copy` as valid action.
   - Actions persisted with `health_score`, `actor`, `timestamp`.
4. Legacy Behavior
   - No regressions to existing `accept_risk` handling for yellow.
   - Legacy `escalate_ocr` payloads remain tolerated for backward compatibility (even if UI no longer surfaces it).
5. Clause Safety and Review
   - High-risk clause families for Ostereo are tagged in templates and always appear in review UI when reconstructed.
   - For any reconstructed high-risk clause, reviewer can see source snippet vs template vs output.
   - Red contracts cannot be marked `reconstruction_complete` without red override recorded.

---

## Out of Scope (V1)
1. Full template-pack authoring UI (template changes managed externally and loaded via config).
2. Entity-level clause diff/merge workflows beyond clause-level review and edit.
3. Production enablement; V1 is admin sandbox only for Ostereo.
4. LLM-based reconstruction/summarization (V1 is template-only).

---

## Open Questions for ROVO / Legal / Ops
1. Ostereo high-risk clause matrix
   - Per contract type, which clauses are high-risk and must always be reviewed when reconstructed?
2. Formal red-case override policy
   - Who may approve red-case reconstruction for Ostereo?
   - What documentation/notes are required?
3. Fallback behavior for missing Ostereo templates
   - For each clause type, is fallback to global/CMG template ever acceptable?
   - If yes, under what risk and contract-type constraints?
