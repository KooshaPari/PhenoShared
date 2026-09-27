# Research

## Repository Fit

phenotype-infra is the canonical infrastructure source for the 7-node compute
mesh, including self-hosted runner routing and the proposed HW mesh agent bus.
ADR 0009 describes agent-to-agent coordination over Tailscale for planner and
heavy-build dispatch flows.

## Decision

The badge is appropriate as governance metadata because this repo controls
agent execution infrastructure. It should remain a README badge only and should
not affect IaC, secrets, runbooks, or runtime configuration.

