# Pipeline Decisions

## Preflight Rollout
**Locked decision:** Current rollout stage is sandbox + ADMIN-only.

### Current Stage
- Feature flag: PREFLIGHT_GATE_SYNC (default OFF)
- Access: ADMIN role only
- Scope: Document quality analysis + gate enforcement

### Rollout Boundary (Locked)
Current stage is ADMIN-only sandbox. No analyst access is implemented or planned in this version.
Any future rollout expansion would require a separate flag and a new design review.

## Page Classification Thresholds (Locked P1E)
- SEARCHABLE: chars >= 50 AND image_ratio <= 0.70
- SCANNED: chars < 50 AND image_ratio >= 0.30
- Otherwise: MIXED

## Gate Thresholds (Locked P1E)
- RED: replacement_char_ratio > 0.05 OR control_char_ratio > 0.03
- YELLOW: doc_mode MIXED OR avg_chars < 30 OR >80% sparse pages
- GREEN: all checks pass
