# Governance Overview

Standards and processes for maintaining PhenoDocs.

## Quality Standards

| Metric | Target | Measurement |
|--------|--------|-------------|
| Broken Links | 0% | Link checker (weekly) |
| Build Success | 100% | CI pipeline |
| Response Time | < 3s | Lighthouse audit |
| Accessibility | 100% | axe-core tests |

## Review Workflow

All reviewable changes follow this fixed sequence:

```text
Draft → Auto-Validation → Review → Approval → Publish
  │             │              │        │         │
  │             │              │        │         └─ Deploy to production
  │             │              │        └─ Approve content
  │             │              └─ Technical review
  │             └─ Link check, build check
  └─ Initial creation
```

## Journey Traceability

Journey docs are part of governance, not optional extras.

- [Journey Traceability](/governance/journeys.md)
- [Phenotype standard](https://github.com/kooshapari/phenotype-infra/blob/main/docs/governance/journey-traceability-standard.md)
- hwLedger remains the reference implementation for `ShotGallery` and
  `RecordingEmbed`

### Stacked PR and Release Ops Governance

- [Stacked PR and Release Governance](/governance/stacked-prs/)
- [Branching and Release Channels](/governance/stacked-prs/01-branching-and-channels)
- [WBS and DAG Rules](/governance/stacked-prs/02-wbs-and-dag)
- [PR Stack Template](/governance/stacked-prs/03-pr-template)
- [Merge Scenarios](/governance/stacked-prs/04-merge-scenarios)
- [Release Matrix Template](/templates/release-matrix-template)

## Roles

### Documentation Lead

- Strategy and governance
- Release coordination
- Quality audits

### Maintainers

- Domain expertise
- Quality control
- Timely updates

### Contributors

- Content creation
- Follow guidelines
- PR reviews

### Reviewers

- Accuracy verification
- Feedback

## Adding Projects

### Addition Criteria

1. **Active project** — Has regular commits
2. **Proper structure** — Follows doc taxonomy
3. **Frontmatter** — All docs have required fields
4. **Owner** — Designated maintainer

### Addition Process

1. **Proposal** — Open issue requesting addition
2. **Review** — Docs lead reviews structure
3. **Integration** — Add to HubGenerator
4. **Verification** — Test build and navigation
5. **Launch** — Merge and announce

## Removing Projects

### Removal Criteria

1. **Abandoned** — No commits > 6 months
2. **Archived** — Project archived
3. **Requested** — Owner requests removal

### Removal Process

1. **Notice** — 30 day warning
2. **Archive** — Move to /archive/
3. **Remove** — Remove from HubGenerator
4. **Update** — Regenerate hub

## Versioning

PhenoDocs follows semantic versioning:

```text
MAJOR.MINOR.PATCH
  │     │     │
  │     │     └─ Bug fixes
  │     └─ New features (backward compatible)
  └─ Breaking changes
```

### Release Schedule

- **Patch**: As needed
- **Minor**: Monthly
- **Major**: As needed (deprecation notice 90 days)

## Security

### Content Security

- Review all user-generated links
- Sanitize markdown
- No executable content

### Access Control

- Write: Maintainers only
- Review: Contributors
- Read: Public

### Data Protection

- No PII in docs
- No credentials in docs
- Regular audits

## Compliance

### Accessibility (WCAG 2.1 AA)

- Alt text for images
- Proper heading hierarchy
- Color contrast
- Keyboard navigation

### Licensing

- All content: MIT or project license
- Dependencies: Compatible licenses

## Monitoring

### Health Checks

| Check | Frequency | Alert |
|-------|-----------|-------|
| Build status | Every commit | Yes |
| Link validity | Weekly | Yes |
| Lighthouse score | Monthly | No |
| Accessibility | Monthly | No |

### Metrics

- Page views
- Search queries
- Build time
- Error rate

## Incident Response

### Broken Build

1. **Detect** — CI failure notification
2. **Investigate** — Check recent changes
3. **Fix** — Revert or patch
4. **Verify** — Confirm build passes
5. **Document** — Update if needed

### Broken Links

1. **Detect** — Weekly link check
2. **Assess** — Internal vs external
3. **Fix** — Update or remove
4. **Verify** — Re-check

## Continuous Improvement

### Retrospectives

- Quarterly doc health review
- Identify gaps
- Plan improvements

### Feedback

- Issue tracker
- Discussion board
- Office hours (monthly)

## Contact

- **Documentation Lead**: @doc-lead
- **Emergency**: #docs-emergency (Slack)
- **General**: #docs (Slack)
