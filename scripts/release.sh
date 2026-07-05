#!/usr/bin/env bash
# OSS Release Script — SemVer bump + CHANGELOG + tag + GH release
# Adapted for sat-centres-workflow (tag-only mode — no pyproject.toml manifest)
#
# Usage:
#   bash scripts/release.sh patch      # 1.0.0 → 1.0.1
#   bash scripts/release.sh minor      # 1.0.0 → 1.1.0
#   bash scripts/release.sh major      # 1.0.0 → 2.0.0
#   bash scripts/release.sh 1.3.0      # explicit version

set -euo pipefail

VERSION_ARG="${1:-}"
if [ -z "$VERSION_ARG" ]; then
  echo "Usage: bash scripts/release.sh <patch|minor|major|x.y.z>"
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Error: working tree has uncommitted changes. Commit or stash first."
  exit 1
fi

# Detect current version from the latest git tag (tag-only project)
CURRENT=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "0.0.0")
echo "Current version: $CURRENT"

semver_bump() {
  local version="$1" bump="$2"
  local major minor patch
  IFS='.' read -r major minor patch <<< "$version"
  case "$bump" in
    major) echo "$((major + 1)).0.0" ;;
    minor) echo "$major.$((minor + 1)).0" ;;
    patch) echo "$major.$minor.$((patch + 1))" ;;
    *)     echo "$bump" ;;
  esac
}

NEW_VERSION=$(semver_bump "$CURRENT" "$VERSION_ARG")
echo "New version:     $NEW_VERSION"
echo ""
read -r -p "Proceed with release v$NEW_VERSION? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

TODAY=$(date +%Y-%m-%d)

# Roll CHANGELOG: move Unreleased items into the new version header
if [ -f "CHANGELOG.md" ]; then
  sed -i.bak \
    "s/## \[Unreleased\]/## [Unreleased]\n\n---\n\n## [$NEW_VERSION] - $TODAY/" \
    CHANGELOG.md
  rm -f CHANGELOG.md.bak

  # Update comparison links at the bottom
  sed -i.bak \
    "s|compare/v.*\.\.\.HEAD|compare/v$NEW_VERSION...HEAD|" \
    CHANGELOG.md
  echo "[$NEW_VERSION]: https://github.com/shauryagangrade/sat-centres-workflow/releases/tag/v$NEW_VERSION" \
    >> CHANGELOG.md
  rm -f CHANGELOG.md.bak

  echo "✓ Updated CHANGELOG.md"
  echo ""
  git diff CHANGELOG.md | head -40
  echo ""
  read -r -p "CHANGELOG looks correct? [y/N] " CHANGELOG_OK
  if [[ ! "$CHANGELOG_OK" =~ ^[Yy]$ ]]; then
    echo "Edit CHANGELOG.md manually, then re-run."
    exit 0
  fi
fi

git add -A
git commit -m "chore: release v$NEW_VERSION"
echo "✓ Release commit created"

git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
git push origin HEAD
git push origin "v$NEW_VERSION"
echo "✓ Tag v$NEW_VERSION pushed"

if command -v gh &>/dev/null; then
  read -r -p "Create GitHub Release for v$NEW_VERSION? [y/N] " GH_RELEASE
  if [[ "$GH_RELEASE" =~ ^[Yy]$ ]]; then
    RELEASE_NOTES=$(awk "/## \[$NEW_VERSION\]/{flag=1; next} /^## \[/{flag=0} flag" CHANGELOG.md)
    if [ -n "$RELEASE_NOTES" ]; then
      gh release create "v$NEW_VERSION" \
        --title "v$NEW_VERSION" \
        --notes "$RELEASE_NOTES" \
        --repo shauryagangrade/sat-centres-workflow
    else
      gh release create "v$NEW_VERSION" \
        --title "v$NEW_VERSION" \
        --generate-notes \
        --repo shauryagangrade/sat-centres-workflow
    fi
    echo "✓ GitHub Release created"
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Release v$NEW_VERSION complete."
echo ""
echo "Post-release checklist:"
echo "  [ ] Announce on social with demo GIF"
echo "  [ ] Post to r/Python or r/SideProject"
echo "  [ ] Update docs if any CLI flags changed"
