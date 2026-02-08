#!/bin/bash
# Orchestrate OS — Repository Cleanup Script
# Run this to untrack large binary assets that are bloating the repo
# and causing corrupt downloads from GitHub.
#
# WHAT THIS DOES:
# 1. Untracks attached_assets/ (Replit screenshots, 166 files, ~11MB)
# 2. Untracks Brand Assets/ (duplicate logos, 5 files, ~9MB)
# 3. Removes biggerMain.svg from assets/brand/ (unused 2.7MB duplicate)
# 4. Removes orchestrate-os-logo.png from assets/brand/ (unused 2MB, app uses SVG)
# 5. Keeps only assets/brand/orchestrate-os-logo.svg (the one file the app uses)
#
# FILES ARE NOT DELETED FROM DISK — only untracked from git.
# .gitignore already prevents re-adding them.
#
# AFTER RUNNING: commit and push to GitHub. The download should work.

set -e

echo "=== Orchestrate OS Repo Cleanup ==="
echo ""

# Step 1: Untrack attached_assets
echo "[1/5] Untracking attached_assets/ (Replit screenshots)..."
git rm --cached -r attached_assets/ 2>/dev/null || echo "  (already untracked)"

# Step 2: Untrack Brand Assets
echo "[2/5] Untracking Brand Assets/ (duplicate logos)..."
git rm --cached -r "Brand Assets/" 2>/dev/null || echo "  (already untracked)"

# Step 3: Remove biggerMain.svg from tracking
echo "[3/5] Untracking assets/brand/biggerMain.svg (unused 2.7MB)..."
git rm --cached "assets/brand/biggerMain.svg" 2>/dev/null || echo "  (already untracked)"

# Step 4: Remove orchestrate-os-logo.png from tracking (app uses SVG)
echo "[4/5] Untracking assets/brand/orchestrate-os-logo.png (unused 2MB)..."
git rm --cached "assets/brand/orchestrate-os-logo.png" 2>/dev/null || echo "  (already untracked)"

# Step 5: Remove cold_route_flow.svg if present (2.7MB, unreferenced)
echo "[5/5] Untracking docs/assets/miro/cold_route_flow.svg (unused 2.7MB)..."
git rm --cached "docs/assets/miro/cold_route_flow.svg" 2>/dev/null || echo "  (already untracked)"

echo ""
echo "=== Cleanup complete ==="
echo ""
echo "Next steps:"
echo "  1. git add .gitignore"
echo "  2. git commit -m 'chore: untrack large binary assets causing corrupt downloads'"
echo "  3. git push"
echo ""
echo "To also clean git history of old binary blobs (optional, advanced):"
echo "  git filter-branch --tree-filter 'rm -rf \"Brand Assets\" attached_assets assets/brand/biggerMain.svg' HEAD"
echo "  git push --force-with-lease"
echo ""
echo "Estimated size reduction: ~25MB from tracked files, ~50-80MB from git history with filter-branch"
