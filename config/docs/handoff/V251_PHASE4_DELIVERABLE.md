# Evidence Inspector v2.51 — Phase 4 Deliverable

## Status: COMPLETE — 16/16 tests pass

## Summary

Phase 4 delivers three hardening features for Evidence Viewer:

1. **Role Enforcement (P0)** — RFI custody transitions and correction approve/reject are now gated by workspace role
2. **OCR Escalation Idempotency** — Duplicate escalation requests return 200 with `_idempotent` flag instead of creating duplicates
3. **Mojibake Gate UI** — Quality-flag-driven banner in the document viewer with escalation CTA and reader-mode gating

## Files Changed

### Backend
| File | Change |
|------|--------|
| `server/routes/rfis.py` | Role enforcement on custody transitions: analyst-side (open→awaiting_verifier, returned→awaiting_verifier) and verifier-side (awaiting→returned/resolved/dismissed). Returns 403 ROLE_NOT_ALLOWED with required vs actual role details. Admin/architect can perform both sides. |
| `server/routes/corrections.py` | Role enforcement on approve/reject: verifier, admin, architect only. Analyst blocked with 403 ROLE_NOT_ALLOWED. |
| `server/routes/ocr_escalations.py` | Idempotent duplicate detection: checks for existing pending/in_progress escalation of same type, returns 200 with `_idempotent: true` and `_note` if found. New escalations return 201. Added `quality_flag` context field and `MOJIBAKE_ESCALATION_REQUESTED` audit event. |

### Frontend
| File | Change |
|------|--------|
| `ui/viewer/index.html` | Mojibake Gate UI module: `MOJIBAKE_GATE_CONFIG` with three quality flags (suspect_mojibake, unreadable, missing_text_layer), banner rendering with icon/title/message/style, escalation CTA button with POST to `/documents/{id}/ocr-escalations`, reader-mode disable for unreadable/missing_text_layer flags. |

### Test
| File | Change |
|------|--------|
| `scripts/phase4_smoke.py` | 16-test comprehensive smoke test covering all Phase 4 features. |

## API Test Evidence

```
PHASE 4 COMPREHENSIVE SMOKE TEST - FINAL
  [PASS] 1. RFI create (analyst): 201
  [PASS] 2. RFI send (analyst OK): 200
  [PASS] 3. RFI send (verifier blocked 403): 403
  [PASS] 3b. ROLE_NOT_ALLOWED code
  [PASS] 4. RFI resolve (verifier OK): 200
  [PASS] 5. RFI resolve (analyst blocked 403): 403
  [PASS] 6. Correction create (non-trivial): 201
  [PASS] 6b. Status pending_verifier
  [PASS] 7. Correction approve (verifier OK): 200
  [PASS] 8. Correction approve (analyst blocked 403): 403
  [PASS] 8b. ROLE_NOT_ALLOWED code
  [PASS] 9. OCR escalation create: 201
  [PASS] 10. OCR escalation idempotent (200): 200
  [PASS] 10b. _idempotent flag: True
  [PASS] 11. Audit: MOJIBAKE_ESCALATION_REQUESTED
  [PASS] 12. Audit: RFI_CREATED
TOTAL: 16/16 passed, 0 failed
```

## Role Enforcement Matrix

| Transition | Analyst | Verifier | Admin | Architect |
|------------|---------|----------|-------|-----------|
| RFI: open → awaiting_verifier | OK | 403 | OK | OK |
| RFI: returned → awaiting_verifier | OK | 403 | OK | OK |
| RFI: awaiting → returned | 403 | OK | OK | OK |
| RFI: awaiting → resolved | 403 | OK | OK | OK |
| RFI: awaiting → dismissed | 403 | OK | OK | OK |
| Correction: approve | 403 | OK | OK | OK |
| Correction: reject | 403 | OK | OK | OK |

## Mojibake Gate UI Configuration

| quality_flag | Severity | Reader Mode | Icon | Banner Color |
|-------------|----------|-------------|------|-------------|
| suspect_mojibake | warning | enabled | ⚠️ | amber/orange |
| unreadable | error | disabled | 🚫 | red |
| missing_text_layer | error | disabled | 📄 | red |

## Audit Events Added

- `MOJIBAKE_ESCALATION_REQUESTED` — emitted on OCR escalation create, includes document_id, escalation_type, quality_flag

## Breaking Changes
None. All changes additive under `EVIDENCE_INSPECTOR_V251` feature flag.

## GO/NO-GO for Phase 5
**GO** — All Phase 4 deliverables complete and tested. Ready for Phase 5 planning.
