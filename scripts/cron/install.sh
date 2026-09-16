#!/usr/bin/env bash
# Install the 10-min cron tick via launchd
set -euo pipefail

PLIST="com.pheno.benchmark.every10m.plist"
SRC="/Users/kooshapari/CodeProjects/Phenotype/pheno-harness/scripts/cron/$PLIST"
DST="$HOME/Library/LaunchAgents/$PLIST"

cp "$SRC" "$DST"
launchctl load "$DST"
echo "Installed: $DST"
echo "Run: launchctl list | grep pheno.benchmark"
