# macOS release signing session

Goal: add a fail-closed Developer ID signing and notarization lane without handling credentials or
changing the development workflow. The release script is explicit-consent only and has a dry-run mode.
