# RULE_LIFECYCLE.md

## 1. Manual Discovery
Operators identify semantic issues during review of datasets or QA packets.

## 2. Drafting
Rules are written as intent statements:
“When I see X, I expect Y”

## 3. Validation
- Schema validation
- Conflict detection
- Completeness checks

## 4. Offline Preview
Rules are applied to example datasets to observe outcomes.

## 5. Patch Export
Validated rules are exported as config_pack.patch.json files.

## 6. PR + Review
Patches are submitted for review with documented intent and preview results.

## 7. Versioning & Changelog
- Every patch increments version
- Changelog entries explain why, not just what
