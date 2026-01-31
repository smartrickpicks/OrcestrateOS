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
