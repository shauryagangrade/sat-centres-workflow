#!/usr/bin/env bash
# Module 3 — Standard GitHub Labels
# Creates the standard OSS label set for sat-centres-workflow.
# Idempotent — skips labels that already exist.
#
# Prerequisites: gh CLI authenticated (gh auth login)
# Usage: bash scripts/setup-labels.sh [owner/repo]

set -euo pipefail

if ! command -v gh &>/dev/null; then
  echo "Error: gh CLI not found. Install from https://cli.github.com" >&2
  exit 1
fi

REPO="${1:-shauryagangrade/sat-centres-workflow}"
echo "Setting up labels for: $REPO"

create_label() {
  local name="$1" color="$2" description="$3"
  if gh label list --repo "$REPO" --json name --jq '.[].name' 2>/dev/null | grep -qx "$name"; then
    echo "  → skipped (exists): $name"
  else
    gh label create "$name" --color "$color" --description "$description" --repo "$REPO"
    echo "  ✓ created: $name"
  fi
}

echo ""
echo "── Core Labels ──"
create_label "bug"              "d73a4a" "Something isn't working"
create_label "enhancement"     "a2eeef" "New feature or request"
create_label "documentation"   "0075ca" "Improvements or additions to documentation"
create_label "question"        "d876e3" "Further information is requested"
create_label "duplicate"       "cfd3d7" "This issue or PR already exists"
create_label "wontfix"         "ffffff" "This will not be worked on"
create_label "invalid"         "e4e669" "This doesn't seem right"

echo ""
echo "── Contributor Labels ──"
create_label "good first issue" "7057ff" "Good for newcomers — scoped and documented"
create_label "help wanted"      "008672" "Extra attention is needed — community contributions welcome"
create_label "mentor available" "0052cc" "Maintainer will mentor implementation"

echo ""
echo "── Priority Labels ──"
create_label "priority: high"   "b60205" "Needs to be addressed soon"
create_label "priority: medium" "fbca04" "Important but not urgent"
create_label "priority: low"    "0e8a16" "Nice to have"

echo ""
echo "── Type Labels ──"
create_label "breaking change" "e11d48" "Changes that break existing functionality"
create_label "security"        "b60205" "Security vulnerability or concern"
create_label "performance"     "0052cc" "Performance improvement"
create_label "dependencies"    "0075ca" "Pull requests that update a dependency file"
create_label "geocoding"       "f9d0c4" "Related to geocoding providers or accuracy"
create_label "pipeline"        "bfd4f2" "Related to the download/normalize/validate pipeline"

echo ""
echo "Done. All standard OSS labels configured for $REPO."
