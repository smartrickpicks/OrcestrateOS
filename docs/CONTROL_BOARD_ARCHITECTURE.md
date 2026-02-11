# CONTROL_BOARD_ARCHITECTURE.md

## Overview
Orchestrate OS (formerly Kiwi Semantic Control Board) is composed of conceptual components that support deterministic rule authoring and review.
These components describe behavior, not implementation.

## Major Components
- Authoring UI: Surface where operators describe rules in structured form.
- Rule Parser: Translates human-authored rules into structured schemas.
- Validator: Checks schema correctness, conflicts, and completeness.
- Preview Engine: Applies rules to example datasets offline.
- Exporter: Produces config_pack patch artifacts.

## Data Flow
1. Human observes pattern or issue
2. Rule is authored in structured form
3. Validator checks rule integrity
4. Preview engine simulates outcomes
5. Exporter generates patch

## Determinism Enforcement
- Strict schemas
- Explicit rule ordering
- No probabilistic logic
- Offline-only evaluation

## Human Judgment Zones
- Pattern recognition
- Rule intent definition
- Conflict resolution decisions
- Final approval during review
