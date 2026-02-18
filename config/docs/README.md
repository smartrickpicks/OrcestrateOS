# Documentation Index

> Orchestrate OS — Offline-first semantic governance for DataDash + Kiwi

## Quick Start

See [INDEX.md](INDEX.md) for the complete table of contents.

## V1 Governance

| Document | Description |
|----------|-------------|
| [Flow Doctrine](V1/Flow-Doctrine.md) | Human+Agent workflow governance (12 stages) |
| [Workflow Spec](specs/Human-Agent-Workflow-V1.json) | Machine-readable workflow specification |
| [Miro Diagram Prompt](assets/miro/Human-Agent-Workflow-MiroPrompt.txt) | Visual diagram generation for Miro |

## UI Documentation

### Principles
| Document | Description |
|----------|-------------|
| [UI Principles](ui/ui_principles.md) | Core principles and Review State Transition Matrix |
| [Gate-View Mapping](ui/gate_view_mapping.md) | Gate-to-view ownership contracts |

### Roles
| Document | Description |
|----------|-------------|
| [Analyst](ui/roles/analyst.md) | Default operator role (load, triage, author) |
| [Verifier](ui/roles/verifier.md) | Elevated review role (approve/reject at verifier gate) |
| [Admin](ui/roles/admin.md) | Full authority (final approval, promotion, export) |

### Views
| Document | Description |
|----------|-------------|
| [Triage View](ui/views/triage_view.md) | Review State summary and navigation hub |
| [Record Inspection](ui/views/single_row_review_view.md) | Single-record detail view |
| [Patch Authoring](ui/views/patch_authoring_view.md) | Patch Studio workbench |
| [Verifier Review](ui/views/verifier_review_view.md) | Review surface for verifiers |
| [Admin Approval](ui/views/admin_approval_view.md) | Final approval surface |
| [Promotion](ui/views/promotion_view.md) | Baseline promotion and PR export |
| [Data Source](ui/views/data_source_view.md) | Add/switch data source |
| [All Data Grid](ui/views/all_data_grid_view.md) | Bulk inspection surface |
| [Record Inspection](ui/views/single_row_review_view.md) | Per-record inspection |
| [AUDIT_LOG](AUDIT_LOG.md) | Append-only evidence ledger |

## Core Principles

- **Determinism**: Same inputs produce identical outputs
- **Auditability**: Every decision has traceable evidence
- **Human Authority**: Operators approve or reject; agents propose only
- **Offline-First**: No network dependencies for validation

## Documentation Structure

```
docs/
├── V1/                    # V1 governance documents
│   └── Flow-Doctrine.md
├── specs/                 # Machine-readable specifications
│   └── Human-Agent-Workflow-V1.json
├── assets/
│   └── miro/              # Visual diagram assets
│       └── Human-Agent-Workflow-MiroPrompt.txt
├── INDEX.md               # Full documentation index
├── overview.md            # Plain-English overview
├── glossary.md            # Term definitions
└── [numbered docs]        # Core explainers (00-14)
```

## Drift Detection

Run the drift sweep script to check for deprecated terminology:

```bash
bash scripts/docs_drift_sweep.sh
```

## Related

- [INDEX.md](INDEX.md) — Complete documentation index
- [CHANGELOG.md](../CHANGELOG.md) — Version history
- [replit.md](../replit.md) — Project configuration
