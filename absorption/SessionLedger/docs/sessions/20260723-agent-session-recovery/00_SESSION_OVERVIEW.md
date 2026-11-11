# Native session resolver

Goal: provide a narrow durable resolver contract for ShareCLI process evidence
to normalized harness conversation IDs and resume recipes.

SessionLedger remains the conversation/transcript authority. It does not own
Ghostty surfaces, PTYs, or process injection.
