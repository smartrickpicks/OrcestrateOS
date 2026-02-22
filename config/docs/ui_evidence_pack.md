# Orchestrate OS — Evidence Pack

Audience
- Analysts authoring patches, Verifiers reviewing, and Admins preparing governance bundles.

Purpose
- Assemble a structured evidence bundle that gates patch submission and supports audit review. Evidence Pack validation enforces identical gates for both Record Inspection and Patch Studio submit surfaces.

## Evidence Pack Blocks (canonical)

| Block | Alias | Description | Required |
|-------|-------|-------------|----------|
| Observation | WHEN | What situation was observed | Yes (Correction) |
| Expected | THEN | What behavior is expected | Yes (Correction) |
| Justification | BECAUSE | Why this change is correct | Yes (all types, min 10 chars) |
| Repro | — | Steps to reproduce | Yes (Correction, unless Override) |

## Replay Contract (v1.6.57)

The Replay Contract captures how a change can be replayed and what result is expected. Validation rules differ by patch type.

| Field | Type | Description |
|-------|------|-------------|
| replay_type | enum | MANUAL, STUBBED, or NA |
| replay_steps | string | Steps to replay the change |
| replay_expected_result | string | Expected outcome of the replay |

### Validation Rules by Patch Type

| Patch Type | replay_type | replay_steps | replay_expected_result |
|------------|-------------|--------------|------------------------|
| Correction | Required (cannot be NA) | Required (min 5 chars) | Required (min 5 chars) |
| Blacklist | Required (cannot be NA) | Required (min 5 chars) | Required (min 5 chars) |
| RFI | Optional (may be NA) | Optional | Optional |

If required replay fields are missing or invalid, submission is blocked with an actionable error message.

## Gate Enforcement

Evidence Pack completeness is enforced at submission time via `validateSubmissionGates()`, a shared validation path used by both Record Inspection and Patch Studio. This ensures gate parity — identical conditions block or allow submission regardless of the submit surface.

| Gate | Check | On Failure |
|------|-------|------------|
| gate_evidence | All required blocks populated per patch type | Block submit, show missing fields |
| gate_replay | Replay contract satisfied per patch type rules | Block submit, show missing replay fields |
| gate_preflight | All preflight checks pass or warn (no fail/pending) | Block submit, show failed checks |

## Submit vs Approval

**Submit creates a patch request — it is not an approval.**
- Submit routes the patch to the Verifier review queue with status `Submitted`.
- No implicit approval state is set by submission.
- The author of a patch cannot approve their own patch (self-approval is blocked).

## Assembly (suggested structure)

```
evidence/
  preview/preview.json
  expected/baseline.json
  expected/edge.json
  validation/report.txt
  smoke/baseline.txt
  smoke/edge.txt (optional)
  patch/patch.json
  notes/identity_keys.txt (contract_key/file_url/file_name)
```

## Determinism
- Normalize JSON keys when comparing; arrays follow stable order by identity keys.
- Same inputs produce identical gate results regardless of submit surface.
