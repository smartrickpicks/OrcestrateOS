#!/bin/bash
# docs_drift_sweep.sh - Scan for deprecated terminology in docs and UI
# Usage: bash scripts/docs_drift_sweep.sh
# Output: Report of deprecated terms found (no auto-edits)

set -e

echo "=========================================="
echo "  Docs Drift Sweep - Terminology Report"
echo "=========================================="
echo ""
echo "Scanning for deprecated terms..."
echo ""

FOUND_DRIFT=0

# Function to search and report
search_term() {
    local term="$1"
    local replacement="$2"
    local context="$3"
    
    echo "--- Checking: \"$term\" ---"
    echo "    Should be: \"$replacement\""
    if [ -n "$context" ]; then
        echo "    Context: $context"
    fi
    
    # Search in docs and ui directories
    RESULTS=$(grep -rn --include="*.md" --include="*.html" --include="*.json" --include="*.txt" "$term" docs/ ui/ 2>/dev/null || true)
    
    if [ -n "$RESULTS" ]; then
        echo "    FOUND:"
        echo "$RESULTS" | while read -r line; do
            echo "      $line"
        done
        FOUND_DRIFT=1
        echo ""
    else
        echo "    OK (not found)"
        echo ""
    fi
}

# Check deprecated terms
search_term "Kiwi Control Board" "Semantic Control Board" ""
search_term "All Data Grid" "All-Data Grid" "Note: hyphenated form is correct"
search_term "Reviewer Hub" "Verifier Review" ""
search_term "\"Queue\"" "specific queue name" "standalone nav label context only"

# Additional checks for common drift patterns
echo "--- Additional Checks ---"
echo ""

# Check for TODO/FIXME comments that might indicate incomplete work
echo "Checking for TODO/FIXME markers..."
TODO_COUNT=$(grep -rn --include="*.md" --include="*.html" "TODO\|FIXME" docs/ ui/ 2>/dev/null | wc -l || echo "0")
echo "    Found $TODO_COUNT TODO/FIXME markers"
echo ""

# Check for placeholder text
echo "Checking for placeholder text..."
PLACEHOLDER=$(grep -rn --include="*.md" --include="*.html" "\[placeholder\]\|TBD\|TBA\|PLACEHOLDER" docs/ ui/ 2>/dev/null || true)
if [ -n "$PLACEHOLDER" ]; then
    echo "    FOUND placeholders:"
    echo "$PLACEHOLDER" | while read -r line; do
        echo "      $line"
    done
else
    echo "    OK (no placeholders found)"
fi
echo ""

# Summary
echo "=========================================="
echo "  Summary"
echo "=========================================="
if [ $FOUND_DRIFT -eq 1 ]; then
    echo "  STATUS: Drift detected (see above)"
    echo "  ACTION: Review and update deprecated terms"
else
    echo "  STATUS: No drift detected"
    echo "  All terminology appears current"
fi
echo "=========================================="
