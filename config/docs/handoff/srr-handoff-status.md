# Record Inspection Handoff Documentation Status

> Audit of documentation coverage for Record Inspection handoffs and role-based workflows.

**Last Updated:** v1.5.2

---

## Documentation Status

### What is Documented Now

| Topic | Location | Status |
|-------|----------|--------|
| Record Inspection layout and field actions | `docs/ui/views/single_row_review_view.md` | Complete |
| Field Inspector 6-state model | `docs/ui/views/single_row_review_view.md` | Complete |
| Evidence Pack structure | `docs/ui/views/single_row_review_view.md` | Complete |
| Verifier Review view contract | `docs/ui/views/verifier_review_view.md` | Complete |
| Analyst role permissions | `docs/ui/roles/analyst.md` | Complete |
| Verifier role permissions | `docs/ui/roles/verifier.md` | Complete |
| Admin role permissions | `docs/ui/roles/admin.md` | Complete |
| Gate ownership mapping | `docs/ui/gate_view_mapping.md` | Complete |
| State transitions per role | `docs/ui/ui_principles.md` | Complete |

### What Was Missing (Now Addressed)

| Topic | Status | Location |
|-------|--------|----------|
| Shared PatchRequest store | Documented | [HANDOFF.md](./HANDOFF.md#shared-patchrequest-store-v152) |
| record_id routing strategy | Documented | [single_row_review_view.md](../ui/views/single_row_review_view.md#record-identity-model-v152) |
| UUID alias capture | Documented | [single_row_review_view.md](../ui/views/single_row_review_view.md#uuid-alias-capture-v152) |
| Debug panel | Documented | [verifier_review_view.md](../ui/views/verifier_review_view.md#debug-panel-v152) |
| Verifier Record Inspection hydration | Documented | [verifier_review_view.md](../ui/views/verifier_review_view.md#srr-hydration-sequence-v152) |
| Artifact Store integration | Documented | [INTERFACES.md](../INTERFACES.md#artifact-store-v152) |
| Queue item schema | Documented | [HANDOFF.md](./HANDOFF.md#queue-item-schema-v152) |

### What Was Updated in Latest Iteration

See **Recent Changes (v1.5.2)** below.

---

## Recent Changes (v1.5.2)

- **Shared PatchRequest Store**: New `PATCH_REQUEST_STORE` with `pr:` localStorage prefix for cross-role access. `createPatchRequest()` saves to both legacy and shared store.

- **record_id Routing (no row index)**: Stable `record_id` generated via `hash(tenant_id + dataset_id + canonicalizeRowForFingerprint(row))`. Replaces row-index-based lookups that broke on sort/filter.

- **Verifier Record Inspection Hydration from patch_request_id**: `vrOpenSingleRowReview()` now loads PatchRequest by `patch_request_id` FIRST, then resolves record by `record_id`. Blocking error UI if PatchRequest not found.

- **UUID Aliases Capture**: During import, `extractUuidAliases()` scans row values for RFC4122 UUIDs and stores in `_identity.aliases[]`. Enables cross-system ID matching.

- **Debug Panel (?debug=1)**: URL param `?debug=1` shows collapsible debug panel with:
  - Current role, tenant_id, division_id, dataset_id
  - record_id, patch_request_id
  - Storage keys with load success/failure indicators (green/red)

---

## Handoff Model Summary

```
Analyst → Verifier → Admin
   │          │          │
   │          │          └─ Admin Approval View
   │          │             (gate_admin owner)
   │          │
   │          └─ Verifier Review View
   │             (gate_verifier owner)
   │
   └─ Record Inspection
      (gate_evidence owner)
```

### Key Handoff Points

1. **Analyst submits patch** → Creates PatchRequest in `PATCH_REQUEST_STORE`, adds queue item with `{dataset_id, record_id, patch_request_id, division_id}`

2. **Verifier opens queue item** → Loads PatchRequest by `patch_request_id`, then loads record by `record_id` from workbook

3. **Verifier approves** → State → `Verifier_Approved`, routes to Admin queue

4. **Admin approves** → State → `Admin_Approved`, eligible for promotion

---

## Related Documents

- [single_row_review_view.md](../ui/views/single_row_review_view.md)
- [verifier_review_view.md](../ui/views/verifier_review_view.md)
- [admin_approval_view.md](../ui/views/admin_approval_view.md)
- [analyst.md](../ui/roles/analyst.md)
- [verifier.md](../ui/roles/verifier.md)
- [admin.md](../ui/roles/admin.md)
- [gate_view_mapping.md](../ui/gate_view_mapping.md)
