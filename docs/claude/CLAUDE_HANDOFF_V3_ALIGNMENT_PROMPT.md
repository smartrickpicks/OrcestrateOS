# Claude Handoff Prompt: V3 Alignment and Task Architecture

Use this prompt with Claude Code as the planning/architecture pass before implementation.

---

You are the architecture/task-manager pass for Orchestrate 3.0.

Repo: `OrcestrateOS`  
Branch: `fix/preflight-contractgen-stabilization`  
Do not make destructive git changes.

Read these files first:
- `docs/roadmap/ORCHESTRATE_3_0_UNIFIED_WORKSPACE.md`
- `docs/adr/ADR-3X-UNIFIED_CONTRACT_WORKSPACE.md`
- `docs/spec/PTL_EDIT_TO_RECORD_INSPECTOR_V2_FLOW.md`
- `docs/checklists/V3_PARITY_AND_CUTOVER_CHECKLIST.md`

Then produce an alignment output with this exact top block:

`ALIGNED: YES|NO`  
`CONFIDENCE: HIGH|MEDIUM|LOW`  
`BLOCKERS: <count>`

Required sections:
1. Findings (severity-ranked) with file/line references for any mismatches.
2. Clarifying questions (only if truly blocking).
3. Proposed implementation phases with concrete task list:
   - Phase 0: spec lock/gates
   - Phase 1: PTL deep-link and route context
   - Phase 2: focused editor + evidence pane
   - Phase 3: ingestion mapping controls (`unmap`, `alias`, immediate doc apply)
   - Phase 4: generation clause composer (payload add/remove, canonical order, live preview)
   - Phase 5: new counterparty creation flow
   - Phase 6: permissions matrix (`Contract Author` test perms, ingestion vs generation split)
   - Phase 7: parity + cutover
4. Risk list + rollback strategy per phase.
5. Replit staging checklist and expected pass criteria.

Constraints:
- Preserve existing patch/audit backbone.
- Keep legacy Review/Evidence fallback until V3 parity is complete.
- Any edit action must remain auditable and permission-gated.
- Explicitly model ingestion-side and generation-side permissions as separate capability domains.

Stop after planning output. Do not implement code in this pass.

---

## Expected Outcome
If `ALIGNED: YES`, implementation can proceed immediately with phase-scoped coding tasks.
If `ALIGNED: NO`, resolve blockers first and regenerate this output.
