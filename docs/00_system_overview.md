# 00 — System Overview: Orchestrate OS v2.5

## What Is Orchestrate OS?

Orchestrate OS is a semantic control board for music industry contract governance. It gives record labels and music companies a single place to load, review, correct, and approve contract data before it flows into downstream systems like Salesforce.

Think of it as a quality control station where every data change is tracked, every correction requires evidence, and every approval goes through the right person.

## Who Uses It?

Four roles collaborate inside the system, each with different permissions:

- **Analyst** — The front-line operator. Loads workbooks, reviews flagged records, drafts corrections (patches), attaches evidence from source PDFs, and submits work for verification.
- **Verifier** — Reviews the Analyst's patches. Tests corrections against source documents. Can approve, reject, or raise an RFI (Request for Information) asking the Analyst to clarify something.
- **Admin** — Makes final promotion decisions. Once a Verifier approves, the Admin promotes the corrected data to canonical truth. Also manages workspace members and configuration.
- **Architect** — System-level access for calibration and baseline configuration. Can access the Truth Config clean-room for setting baselines.

There is also a **Stakeholder** role (read-only on decision points) envisioned for future notification streams.

## The Contract-as-Channel Model

The core metaphor in v2.5 is: **one contract = one channel**.

Like a Slack or Discord channel dedicated to a single topic, each contract in Orchestrate OS has its own event stream. Every action — from initial upload through final approval — is a timestamped event in that contract's history. The key difference: visibility is permission-scoped. An Analyst's draft patch is like a Discord ephemeral message — only they can see it until they submit it. A Verifier only gets pinged when there's something actionable for them.

This model structures collaboration without noise. People only see what they need to act on.

## Three Planes of Operation

All activity flows through three planes:

### Discovery Plane (Noisy)
Where raw data enters the system. Workbook uploads, data extraction, signal generation, anomaly detection. This plane is messy by design — it catches everything so the Control Room can filter what matters.

### Control Room (Orchestrate OS)
Where meaning is governed before enforcement. Analysts triage flagged records, draft corrections with evidence, and submit patches. Verifiers test and approve. Admins promote to truth. Two lanes run through the Control Room:
- **Hot Route** — Fast path for corrections. Signals flag issues, Analysts fix them, retry if needed. If retries fail, the issue escalates to the Cold Route.
- **Cold Route** — Deliberate path for promotions and approvals. Every step is gated and recorded. No failure goes unrecorded.

### Execution Plane (Quiet)
Where truth must be provable. Finalized data exports to Google Drive or downloads as Excel files. Downstream systems (Salesforce, dashboards) consume only data that has passed through governance.

## Four Gates

Every action in the system must pass through one or more gates:

1. **Evidence Gate** — No patch moves forward without attached evidence from source documents (PDFs, contracts). Blocks if missing.
2. **Naming Gate** — All exported artifacts follow strict status-based naming: `{name}__{STATUS}__{date}__{workspace}.xlsx`. Blocks if invalid.
3. **Validation Gate** — Data must pass schema validation, duplicate account checks, and address completeness. Blocks if invalid.
4. **Role Authority Gate** — No self-approval. Promotion requires Verifier approval followed by Admin promotion. The system enforces this — it's not a suggestion.

## Architecture: What Powers It

### Backend
- **FastAPI** server running on Python, serving both the API and the frontend
- **PostgreSQL** (Neon-backed) for all persistent data — workspaces, batches, patches, members, audit events, Drive connections
- **19 API resource routes** under `/api/v2.5/` — Workspace, Batch, Patch, Contract, Document, Account, Annotation, EvidencePack, RFI, TriageItem, Signal, SelectionCapture, AuditEvent, SSE stream, Health, Sessions, Members, Drive, Auth
- **ULID primary keys** across all tables for sortable, unique identifiers
- **Optimistic concurrency** — stale writes return 409 STALE_VERSION errors

### Authentication
- **Google OAuth (OIDC)** for human users — Google Sign-In flow with backend ID token verification, email-based user matching, and JWT session tokens (HS256, 24-hour expiry)
- **Scoped API keys** for service ingestion (machine-to-machine)
- **Inactive user denial** — checked on every authenticated request
- **Role simulation** — Admin/Architect can simulate Analyst or Verifier roles in sandbox mode for testing. All simulated actions are tagged in audit events.

### Google Drive Integration
- **Two-way integration** — import workbooks from Drive, export finalized workbooks back to Drive
- **OAuth-scoped connections** per workspace — connect, browse folders, import files, export with status-based naming
- **Root folder** set to a specific shared contracts folder for organized file management
- **Import provenance** tracked in the database — every file imported from Drive has a full audit trail
- **Manual refresh only** — no automatic sync; analysts control when data flows in

### Frontend
- **Browser-based application** — a static viewer (`ui/viewer/`) with vanilla JavaScript handles the primary control board interface
- **Modular architecture** — 55+ extracted modules organized into `AppModules.Components.*` and `AppModules.Engines.*` namespaces
- **IndexedDB** for workbook session caching (no localStorage for large data)
- **Audit Timeline** backed by IndexedDB for all governance actions

### Data Flow
- **Config Pack Model** — base configuration + patches, with strict version matching
- **12-status lifecycle** for patch requests (10 visible + 2 hidden)
- **Change Map Engine** tracking cell-level changes
- **Signal Engine** generating deterministic cell-level signals from semantic rules (`field_meta.json`, `qa_flags.json`)
- **Contract Index Engine** building hierarchy: batch → contract → document → section → row

## Workspace Isolation

All data is scoped to a workspace. A single PostgreSQL database uses `workspace_id` foreign keys and composite indexes to keep workspaces isolated. This means multiple organizations can use the system without seeing each other's data.

## Determinism

Given the same inputs and rules, the system always produces the same outputs. Semantic rules follow a WHEN/THEN pattern. Signals are generated deterministically on dataset load. There is no randomness, no AI inference in the governance path — every decision is explicit, traceable, and auditable.

## What This System Is NOT

- **Not a runtime execution engine** — It governs data, it doesn't process transactions
- **Not an AI system** — Discovery plane may use LLM outputs, but the Control Room is entirely deterministic and human-governed
- **Not a chat application** — The channel metaphor describes event streams, not messaging
- **Not a replacement for Salesforce** — It sits upstream, ensuring data quality before it reaches Salesforce
