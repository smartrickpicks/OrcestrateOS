# 00 — System Overview (Semantic Control Plane)

## Intended Audience
Operators, Analysts, and Reviewers responsible for authoring and approving semantic rules.

## Purpose
Provide a high-level orientation to the governance-only semantic control plane: what it owns, how it remains deterministic and offline, and how artifacts flow through the control board.

## Outline
- What This Is
  - A governance-only control plane that defines semantic truth as configuration
  - Offline, deterministic preview of rules on synthetic examples
- What This Is Not
  - No runtime execution, no APIs, no credentials, no prompts
- Canonical Interfaces (see docs/INTERFACES.md)
  - config_pack.base.json (versioned base)
  - config_pack.patch.json (changes[])
  - standardized_dataset (sheeted format)
  - sf_packet (preview output)
- Join Strategy
  - contract_key → file_url → file_name
  - No fabricated identifiers
- Determinism
  - Offline-only; identical inputs yield identical outputs
- Truth & Versioning (see docs/TRUTH_SNAPSHOT.md)
  - Semantic truth = base + approved patches
  - Changelog documents why changes were made
- Governance Lifecycle (see docs/RULE_LIFECYCLE.md)
  - Discover → Draft → Validate → Preview → Export → PR/Review → Version
- Where to Start
  - Read docs/INDEX.md, then run local validation and preview
