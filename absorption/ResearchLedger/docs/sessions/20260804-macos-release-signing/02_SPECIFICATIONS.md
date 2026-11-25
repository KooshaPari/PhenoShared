# Specifications

- The committed configuration contains only an identity environment-variable name and a notarytool
  profile name; it contains no credential.
- A production invocation requires `--confirm-release` and a Developer ID identity supplied through
  the configured environment variable.
- A dry run must not invoke any system release tool.
- Verification must precede submission and must include signature, runtime, entitlement, staple, and
  Gatekeeper checks.
