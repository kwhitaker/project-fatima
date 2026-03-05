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

# -- Colors --
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

log_info()    { echo -e "${CYAN}[ralph]${RESET} $1"; }
log_success() { echo -e "${GREEN}[ralph]${RESET} $1"; }
log_warn()    { echo -e "${YELLOW}[ralph]${RESET} $1"; }
log_error()   { echo -e "${RED}[ralph]${RESET} $1"; }
log_header()  { echo -e "${BOLD}$1${RESET}"; }

# -- Helpers --
count_stories() {
  jq '[.userStories | length] | first' "$PRD_FILE" 2>/dev/null || echo 0
}

count_passed() {
  jq '[.userStories[] | select(.passes == true)] | length' "$PRD_FILE" 2>/dev/null || echo 0
}

count_pending() {
  jq '[.userStories[] | select(.passes == false)] | length' "$PRD_FILE" 2>/dev/null || echo 0
}

format_elapsed() {
  local seconds=$1
  local mins=$((seconds / 60))
  local secs=$((seconds % 60))
  if [ "$mins" -gt 0 ]; then
    echo "${mins}m ${secs}s"
  else
    echo "${secs}s"
  fi
}

# -- Preflight checks --
if ! command -v jq >/dev/null 2>&1; then
  log_error "jq is required (used to parse ralph/prd.json)."
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  log_error "claude (Claude Code) not found in PATH."
  exit 1
fi

if [ ! -f "$PRD_FILE" ]; then
  log_error "$PRD_FILE not found."
  exit 1
fi

mkdir -p "$ARCHIVE_DIR"

# -- Archive previous run if branch changed --
if [ -f "$LAST_BRANCH_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")

  if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
    DATE=$(date +%Y-%m-%d)
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"

    log_info "Archiving previous run: $LAST_BRANCH"
    mkdir -p "$ARCHIVE_FOLDER"
    cp "$PRD_FILE" "$ARCHIVE_FOLDER/" || true
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/" || true
    log_info "Archived to: $ARCHIVE_FOLDER"

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

# -- Track current branch --
CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
if [ -n "$CURRENT_BRANCH" ]; then
  echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
fi

# -- Initialize progress file if it doesn't exist --
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

# -- Early exit: no pending stories --
TOTAL=$(count_stories)
PASSED=$(count_passed)
PENDING=$(count_pending)

if [ "$PENDING" -eq 0 ]; then
  log_success "All $TOTAL stories already complete. Nothing to do."
  exit 0
fi

echo ""
log_header "==============================================================="
log_header "  Ralph (Claude Code) — Starting"
log_info "Branch:     $CURRENT_BRANCH"
log_info "Progress:   $PASSED/$TOTAL stories complete, $PENDING remaining"
log_info "Max iterations: $MAX_ITERATIONS"
log_header "==============================================================="
echo ""

for i in $(seq 1 "$MAX_ITERATIONS"); do
  # -- Check for remaining work --
  PENDING=$(count_pending)
  if [ "$PENDING" -eq 0 ]; then
    echo ""
    log_success "All stories complete!"
    exit 0
  fi

  PASSED=$(count_passed)

  # -- Find the next pending story --
  NEXT_STORY=$(jq -r '[.userStories[] | select(.passes == false)] | first' "$PRD_FILE" 2>/dev/null || echo "")

  if [ "$NEXT_STORY" = "null" ] || [ -z "$NEXT_STORY" ]; then
    log_success "No more pending stories. All done!"
    exit 0
  fi

  STORY_ID=$(echo "$NEXT_STORY" | jq -r '.id // "unknown"' 2>/dev/null || echo "unknown")
  STORY_TITLE=$(echo "$NEXT_STORY" | jq -r '.title // "unknown"' 2>/dev/null || echo "unknown")
  STORY_DESC=$(echo "$NEXT_STORY" | jq -r '.description // ""' 2>/dev/null || echo "")

  # -- Record pre-iteration state for verification --
  COMMIT_BEFORE=$(git rev-parse HEAD 2>/dev/null || echo "none")
  PASSES_BEFORE=$(jq -r --arg id "$STORY_ID" '[.userStories[] | select(.id == $id)] | first | .passes' "$PRD_FILE" 2>/dev/null || echo "unknown")

  echo ""
  log_header "==============================================================="
  log_info "Iteration $i of $MAX_ITERATIONS  |  Progress: ${GREEN}$PASSED${RESET}/${TOTAL} complete"
  log_header "  [$STORY_ID] $STORY_TITLE"
  echo -e "${DIM}"
  echo "$STORY_DESC" | fold -s -w 60 | sed 's/^/  /'
  echo -e "${RESET}"
  log_header "---------------------------------------------------------------"

  ITER_START=$(date +%s)
  LOGFILE="$SCRIPT_DIR/logs/iteration-${i}-${STORY_ID}.log"
  mkdir -p "$SCRIPT_DIR/logs"

  log_info "Claude is working… (log: ${LOGFILE})"

  # Run claude in a new session (setsid -w) so it has no controlling terminal.
  # Without this, claude writes progress/status directly to /dev/tty, which
  # bypasses stdout/stderr redirection and overwrites the script's output.
  setsid -w claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md" > "$LOGFILE" 2>&1 || true

  ITER_END=$(date +%s)
  ELAPSED=$((ITER_END - ITER_START))

  echo ""
  log_header "---------------------------------------------------------------"
  log_info "Iteration $i finished in $(format_elapsed $ELAPSED)"

  # -- Post-iteration verification --
  COMMIT_AFTER=$(git rev-parse HEAD 2>/dev/null || echo "none")
  PASSES_AFTER=$(jq -r --arg id "$STORY_ID" '[.userStories[] | select(.id == $id)] | first | .passes' "$PRD_FILE" 2>/dev/null || echo "unknown")

  # Check if a new commit was made
  if [ "$COMMIT_BEFORE" = "$COMMIT_AFTER" ]; then
    log_warn "No new commits were made this iteration"
  else
    NEW_COMMITS=$(git log --oneline "$COMMIT_BEFORE".."$COMMIT_AFTER" 2>/dev/null | head -5)
    log_success "New commits:"
    echo "$NEW_COMMITS" | sed 's/^/    /'
  fi

  # Check if passes flipped
  if [ "$PASSES_BEFORE" = "false" ] && [ "$PASSES_AFTER" = "true" ]; then
    log_success "[$STORY_ID] marked as PASSED"
  elif [ "$PASSES_BEFORE" = "false" ] && [ "$PASSES_AFTER" = "false" ]; then
    log_warn "[$STORY_ID] still not marked as passed — progress may not have been committed"
  fi

  log_header "==============================================================="

  # -- Check for completion signal --
  if grep -q "<promise>COMPLETE</promise>" "$LOGFILE" 2>/dev/null; then
    echo ""
    log_success "Ralph completed all tasks."
    exit 0
  fi

  sleep 2
done

echo ""
log_warn "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
log_info "Progress: $(count_passed)/$TOTAL stories complete."
log_info "Check ralph/progress.txt for status."
exit 1
