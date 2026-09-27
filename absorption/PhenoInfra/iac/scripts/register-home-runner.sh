#!/usr/bin/env bash
# Justification (scripting policy): 5-line glue — writes a launchd plist for
# woodpecker-agent on macOS. Rust equivalent would reimplement plutil for no gain.
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/com.phenotype.woodpecker-agent.plist"
install -d "$(dirname "$PLIST")"
cat > "$PLIST" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key><string>com.phenotype.woodpecker-agent</string>
    <key>ProgramArguments</key>
    <array>
      <string>/opt/homebrew/bin/woodpecker-agent</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
      <key>WOODPECKER_CONFIG</key>
      <string>/Users/USER_PLACEHOLDER/Library/Application Support/woodpecker-agent/config.env</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>/tmp/woodpecker-agent.log</string>
    <key>StandardErrorPath</key><string>/tmp/woodpecker-agent.err</string>
  </dict>
</plist>
PLIST
echo "Wrote $PLIST — edit USER_PLACEHOLDER then: launchctl load $PLIST"
