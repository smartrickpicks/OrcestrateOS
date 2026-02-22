# ADR-3X: Unified Contract Workspace

## Status
Accepted (implementation planning)

## Context
Current contract operations are split across PTL modal interactions, Record Inspector, Review/Evidence views, and Contract Generator flows. This fragmentation increases handoff friction, duplicated actions, and context loss between ingest, edit, and submit.

The product direction is to unify these into one primary operational workspace while preserving existing patch governance and audit behavior.

## Decision
Adopt `Record Inspector V2 (Beta)` as the unified contract workspace in V3.

Key decision points:
- PTL remains the gate and launches focused edit contexts into workspace.
- PTL `Edit` opens a full workspace route, not an in-place edit modal.
- Any field/status/value change requires evidence/reason capture.
- `Green` gate still requires explicit manual review attestation.
- Ingestion-side mapping controls include unmap and alias creation from raw non-highlighted text.
- Alias rules apply immediately for the active document context.
- Generation-side composition uses payload-based clause inclusion with canonical ordering.
- Permissions are domain-scoped to ingestion-side vs generation-side authoring actions.
- Existing patch submission model remains unchanged as the backend contract.
- Legacy Review/Evidence views remain available behind fallback until parity is proven.

## Consequences
Positive:
- Single-source workflow for analyst and verifier actions.
- Better continuity between extraction context and human correction.
- Cleaner long-term path toward role-specialized authoring and Airlock expansion.
- Clear boundary between ingestion corrections and generation authoring operations.

Negative:
- Significant UI routing and state-linking complexity in transition period.
- Need strict parity testing to avoid regressions in verifier/admin flows.
- Additional complexity in permission configuration and audit granularity.

## Alternatives Considered
- Keep Contract Generator as separate tool and only improve PTL modal UX.
  - Rejected: continues context handoff friction and split mental model.
- Deprecate old views immediately.
  - Rejected: too risky before parity proof and cutover validation.

## Implementation Guardrails
- Feature flag for `Record Inspector V2 (Beta)` route enablement.
- No destructive removal of legacy flows before cutover criteria are met.
- Audit events required for all mutation actions.
- Permission checks must remain explicit per action.

## Open Follow-ups
- Final production naming for V2 workspace.
- Long-term role taxonomy and custom-permission editor design.
- Corrupt-document reconstruction mode and generated-draft custody model.
