#!/bin/bash
# Ralph loop runner (Claude Code)
# Usage: ./ralph/ralph.sh [max_iterations]

set -euo pipefail

MAX_ITERATIONS=${1:-10}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required (used to parse ralph/prd.json)."
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "Error: claude (Claude Code) not found in PATH."
  exit 1
fi

if [ ! -f "$PRD_FILE" ]; then
  echo "Error: $PRD_FILE not found."
  exit 1
fi

mkdir -p "$ARCHIVE_DIR"

# Archive previous run if branch changed
if [ -f "$LAST_BRANCH_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")

  if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
    DATE=$(date +%Y-%m-%d)
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"

    echo "Archiving previous run: $LAST_BRANCH"
    mkdir -p "$ARCHIVE_FOLDER"
    cp "$PRD_FILE" "$ARCHIVE_FOLDER/" || true
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/" || true
    echo "Archived to: $ARCHIVE_FOLDER"

    # Reset progress file for new run
    {
      echo "# Ralph Progress Log"
      echo ""
      echo "## Codebase Patterns"
      echo "- (add stable patterns here as they are discovered)"
      echo ""
      echo "---"
      echo "Started: $(date '+%Y-%m-%d')"
      echo "---"
      echo ""
    } > "$PROGRESS_FILE"
  fi
fi

# Track current branch
CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
if [ -n "$CURRENT_BRANCH" ]; then
  echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
fi

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
  {
    echo "# Ralph Progress Log"
    echo ""
    echo "## Codebase Patterns"
    echo "- (add stable patterns here as they are discovered)"
    echo ""
    echo "---"
    echo "Started: $(date '+%Y-%m-%d')"
    echo "---"
    echo ""
  } > "$PROGRESS_FILE"
fi

echo "Starting Ralph (Claude Code) - Max iterations: $MAX_ITERATIONS"

for i in $(seq 1 "$MAX_ITERATIONS"); do
  # Find the next pending story
  NEXT_STORY=$(jq -r '[.userStories[] | select(.passes == false)] | first' "$PRD_FILE" 2>/dev/null || echo "")
  STORY_ID=$(echo "$NEXT_STORY" | jq -r '.id // "unknown"' 2>/dev/null || echo "unknown")
  STORY_TITLE=$(echo "$NEXT_STORY" | jq -r '.title // "unknown"' 2>/dev/null || echo "unknown")
  STORY_DESC=$(echo "$NEXT_STORY" | jq -r '.description // ""' 2>/dev/null || echo "")

  echo ""
  echo "==============================================================="
  echo "  Ralph Iteration $i of $MAX_ITERATIONS"
  echo "  Story: [$STORY_ID] $STORY_TITLE"
  echo "---------------------------------------------------------------"
  # Word-wrap description at ~60 chars for readability
  echo "$STORY_DESC" | fold -s -w 60 | sed 's/^/  /'
  echo "==============================================================="

  TMPFILE=$(mktemp)
  trap 'rm -f "$TMPFILE"' EXIT
  claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee "$TMPFILE" || true

  if grep -q "<promise>COMPLETE</promise>" "$TMPFILE"; then
    echo ""
    echo "Ralph completed all tasks."
    exit 0
  fi

  echo "Iteration $i complete."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check ralph/progress.txt for status."
exit 1
