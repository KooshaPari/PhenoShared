#!/usr/bin/env sh
# promptscrape updater.
#
# Re-runs the installer against the latest release. Equivalent to running
# `promptscrape update` when the binary is already installed.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/KooshaPari/PhenoShared/main/scripts/update-promptscrape.sh | sh
set -eu

REPO="KooshaPari/PhenoShared"
URL="https://raw.githubusercontent.com/${REPO}/main/scripts/install-promptscrape.sh"

echo "Updating promptscrape from ${URL}..."
curl -fsSL "$URL" | sh
