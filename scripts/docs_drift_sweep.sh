#!/bin/bash
# docs_drift_sweep.sh - Enforce canonical terminology policy
# Usage: bash scripts/docs_drift_sweep.sh
# Output: PASS/FAIL report with allowed exceptions

set -e

echo "=========================================="
echo "  Terminology Drift Guard"
echo "  Canonical Policy Enforcement"
echo "=========================================="
echo ""

FAIL_COUNT=0
WARN_COUNT=0

ALLOWED_EXCEPTIONS=(
  "single_row_review"
  "record_id"
  "row_index"
  "raw_row_index"
  "sheet_name"
  "sheet_mapping"
  "sheet_order"
  "workbook.sheets"
  "contract_key"
  "file_url"
  "file_name"
  "isReferenceSheet"
  "isMetaSheet"
  "sheetCounts"
  "sheetNames"
  "sheet.rows"
  "addSheet"
  "sheet_to_json"
  "getSheet"
)

check_banned_term() {
  local term="$1"
  local replacement="$2"
  local scope="$3"
  local allow_pattern="$4"

  local results
  if [ "$scope" = "docs" ]; then
    results=$(grep -rn --include="*.md" --include="*.json" -i "$term" docs/ 2>/dev/null || true)
  elif [ "$scope" = "ui" ]; then
    results=$(grep -n -i "$term" ui/viewer/index.html 2>/dev/null || true)
  elif [ "$scope" = "config" ]; then
    results=$(grep -rn --include="*.json" -i "$term" config/ 2>/dev/null || true)
  elif [ "$scope" = "server" ]; then
    results=$(grep -rn --include="*.py" -i "$term" server/ 2>/dev/null || true)
  else
    results=$(grep -rn --include="*.md" --include="*.html" --include="*.json" --include="*.py" -i "$term" docs/ ui/ config/ server/ 2>/dev/null || true)
  fi

  if [ -n "$allow_pattern" ]; then
    results=$(echo "$results" | grep -v -E "$allow_pattern" || true)
  fi

  if [ -n "$results" ]; then
    local count
    count=$(echo "$results" | wc -l | tr -d ' ')
    echo "FAIL: \"$term\" found ($count hits) — should be \"$replacement\" [$scope]"
    echo "$results" | head -10 | while read -r line; do
      echo "  $line"
    done
    if [ "$count" -gt 10 ]; then
      echo "  ... and $((count - 10)) more"
    fi
    echo ""
    FAIL_COUNT=$((FAIL_COUNT + count))
    return 1
  else
    echo "PASS: \"$term\" clean [$scope]"
    return 0
  fi
}

echo "--- Rule 1: Reviewer → Verifier ---"
echo ""

check_banned_term "Reviewer" "Verifier" "docs" \
  "Reviewer Hub|Reviewer_Responded|Reviewer_Approved|ReviewerResponded|reviewer_responded|REVIEWER_APPROVED|legacy alias|forbidden|banned|deprecated.term|NEVER use|Reviewer Review|old.*Reviewer" || true

check_banned_term "Reviewer" "Verifier" "ui" \
  "Reviewer_Responded|Reviewer_Approved|ReviewerResponded|reviewer_responded|REVIEWER_APPROVED|role === .Reviewer|normalizeRole" || true

check_banned_term "Reviewer" "Verifier" "config" "" || true
check_banned_term "Reviewer" "Verifier" "server" "" || true

echo ""
echo "--- Rule 2: Single Row Review → Record Inspection (user-facing) ---"
echo ""

check_banned_term "Single Row Review" "Record Inspection" "docs" \
  "single_row_review|Canonical surface|canonical.*name|internal.*token|internal.*route|gate_view_mapping|HANDOFF.*terminology|single-row-review-view.md|legacy_label|legacy.*token" || true

check_banned_term "Single Row Review" "Record Inspection" "ui" \
  "single_row_review|singleRowReview|page-row|srr-|SRR|srrState" || true

check_banned_term "Single Row Review" "Record Inspection" "server" "" || true

echo ""
echo "--- Rule 3: Deprecated surface names ---"
echo ""

check_banned_term "Kiwi Control Board" "Semantic Control Board" "all" \
  "forbidden|banned|deprecated|NEVER use|legacy|old.*new|Semantic Control Board" || true
check_banned_term "Reviewer Hub" "Verifier Review" "all" \
  "forbidden|Forbidden|banned|deprecated|NEVER use|legacy|old.*new|Verifier Review" || true

echo ""
echo "--- Rule 4: Admin Panel is canonical page name ---"
echo ""

ADMIN_DRIFT=$(grep -rn --include="*.md" --include="*.html" -i "Admin Dashboard\|Admin Home\|Admin Settings" docs/ ui/ 2>/dev/null || true)
if [ -n "$ADMIN_DRIFT" ]; then
  echo "WARN: Non-canonical admin naming found:"
  echo "$ADMIN_DRIFT" | head -5
  WARN_COUNT=$((WARN_COUNT + 1))
else
  echo "PASS: Admin Panel naming consistent"
fi

echo ""
echo "--- Allowed Internal Tokens (verified present) ---"
echo ""
for token in single_row_review record_id row_index sheet_name contract_key file_url file_name; do
  count=$(grep -rn --include="*.html" --include="*.js" "$token" ui/ 2>/dev/null | wc -l | tr -d ' ')
  echo "  $token: $count references (internal, allowed)"
done

echo ""
echo "--- Additional Checks ---"
echo ""

TODO_COUNT=$(grep -rn --include="*.md" --include="*.html" "TODO\|FIXME" docs/ ui/ 2>/dev/null | wc -l || echo "0")
echo "  TODO/FIXME markers: $TODO_COUNT"

PLACEHOLDER=$(grep -rn --include="*.md" --include="*.html" "\[placeholder\]\|PLACEHOLDER" docs/ ui/ 2>/dev/null | wc -l || echo "0")
echo "  Placeholder text: $PLACEHOLDER"

echo ""
echo "=========================================="
echo "  Summary"
echo "=========================================="
if [ $FAIL_COUNT -gt 0 ]; then
  echo "  STATUS: FAIL — $FAIL_COUNT terminology violations found"
  echo "  ACTION: Fix user-facing text to use canonical terms"
  echo "  WARNINGS: $WARN_COUNT"
  exit 1
else
  echo "  STATUS: PASS — all canonical terms enforced"
  echo "  WARNINGS: $WARN_COUNT"
  echo "  Internal tokens preserved (single_row_review, record_id, etc.)"
fi
echo "=========================================="
