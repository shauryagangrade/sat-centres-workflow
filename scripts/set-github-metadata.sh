#!/usr/bin/env bash
# Module 1 — GitHub Metadata
# Run this once after pushing to GitHub to set description, topics, and homepage.
#
# Prerequisites: gh CLI authenticated (gh auth login)
# Usage: bash scripts/set-github-metadata.sh

set -euo pipefail

OWNER="shauryagangrade"
REPO="sat-centres-workflow"

echo "Setting GitHub metadata for $OWNER/$REPO …"

gh repo edit "$OWNER/$REPO" \
  --description "A Python CLI to download, process, geocode, validate, and export SAT examination centres." \
  --add-topic sat \
  --add-topic geocoding \
  --add-topic python \
  --add-topic cli \
  --add-topic data-pipeline \
  --add-topic nominatim \
  --add-topic geopy \
  --add-topic pydantic

echo ""
echo "✓ Description and topics set."
echo ""
echo "Optional — add a homepage URL if you have one:"
echo "  gh repo edit $OWNER/$REPO --homepage \"https://your-site.example.com\""
echo ""
echo "Post-setup: visit https://github.com/$OWNER/$REPO and verify the About panel."
