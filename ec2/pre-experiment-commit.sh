#!/usr/bin/env bash
# ─────────────────────────────────────────────
# ec2/pre-experiment-commit.sh
#
# Auto-commit all changes before an experiment runs.
# Called by experiment skills (run-experiment, run-sweep).
# Tags the commit with the experiment/sweep name.
#
# Usage: ./ec2/pre-experiment-commit.sh [experiment-name]
# ─────────────────────────────────────────────
set -euo pipefail

EXPERIMENT_NAME="${1:-experiment-$(date +%Y%m%d-%H%M%S)}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# Check if git repo exists
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "[pre-commit] Not a git repo, skipping auto-commit."
    exit 0
fi

# Check for uncommitted changes
if git diff --quiet HEAD 2>/dev/null && git diff --cached --quiet 2>/dev/null && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo "[pre-commit] Working tree clean, no commit needed."
else
    git add -A
    git commit -m "pre-experiment snapshot: ${EXPERIMENT_NAME}

Auto-committed before running experiment.
Code state at this commit was used for: ${EXPERIMENT_NAME}"
    echo "[pre-commit] Committed changes before ${EXPERIMENT_NAME}"
fi

# Push if remote exists
if git remote get-url origin &>/dev/null; then
    git push origin HEAD 2>/dev/null && echo "[pre-commit] Pushed to origin" || echo "[pre-commit] Push failed (non-fatal)"
fi

# Output the commit SHA for experiment tracking
COMMIT_SHA=$(git rev-parse --short HEAD)
echo "[pre-commit] Code version: ${COMMIT_SHA}"
echo "COMMIT_SHA=${COMMIT_SHA}"
