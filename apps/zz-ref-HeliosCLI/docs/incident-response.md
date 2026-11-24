# Incident Response Playbook - Helios CLI

This document outlines the procedures for responding to incidents affecting the Helios CLI tool, its distribution channels, and end-user execution environments.

## 1. Severity Levels

| Level | Name         | Description                                                                 | Example Impact                                      |
|-------|--------------|-----------------------------------------------------------------------------|-----------------------------------------------------|
| **P0** | Critical     | CLI is completely unusable, distribution servers compromised, or data leak. | Global installation failure, authentication bypass. |
| **P1** | High         | Major feature regression or broken update path for existing users.          | `helios update` fails, core command crashes.        |
| **P2** | Medium       | Non-critical feature failure or platform-specific incompatibility.          | Error on Windows ARM, flag parsing issues.          |
| **P3** | Low          | Cosmetic issues, documentation errors, or minor performance tweaks.        | Typos in help text, slow startup on rare configs.   |

## 2. Response Times

| Severity | Acknowledgment | First Response | Resolution Target |
|----------|----------------|----------------|-------------------|
| **P0**   | 15 minutes     | 30 minutes     | 4 hours           |
| **P1**   | 1 hour         | 2 hours        | 12 hours          |
| **P2**   | 4 hours        | 1 business day | 2 business days   |
| **P3**   | 1 business day | 2 business days| Next Release      |

## 3. Escalation Matrix

| Level | Role                                    | Contact Method       |
|-------|-----------------------------------------|----------------------|
| 1     | CLI Maintainer (On-call)                | Slack / Email        |
| 2     | Technical Lead                          | Phone / Slack DM     |
| 3     | Project Owner / Community Lead          | Emergency Bridge     |

## 4. Communication Templates

### Internal Notification (Slack/Teams)
```markdown
:rotating_light: **[P{X}] Helios CLI Incident: [Brief Title]**
*Status:* Investigating
*Impact:* [Description of user/CLI impact]
*Lead:* [Name]
*Channel:* #helios-incidents-[ticket-id]
```

### GitHub Issue Template (User-facing)
```markdown
**Title:** [P{X}] Critical Failure in `helios [command]`
**Description:** A known issue is currently affecting Helios CLI users. 
**Workaround:** [If available, e.g., "Use version X.Y.Z"]
**Status:** Investigating
```

## 5. Post-Mortem Template

### Incident Summary
- **Date/Time of Incident:** YYYY-MM-DD HH:MM UTC
- **Duration:** X hours Y minutes
- **Severity:** P0 / P1 / P2 / P3
- **Authors:** [List of authors]

### Impact
- **User Impact:** [Number of installs affected / Feedback channels]
- **Tool Impact:** [Specific commands/modules affected]

### Timeline (UTC)
- **HH:MM:** [Event]
- **HH:MM:** [Event]
- ...

### Root Cause Analysis
[Detailed explanation of the code change, build process, or environment issue.]

### What went well?
- [Item 1]
- [Item 2]

### What didn't go well?
- [Item 1]
- [Item 2]

### Action Items
| Action Item | Owner | Priority | Status |
|-------------|-------|----------|--------|
| [Task 1]    | Name  | High     | Open   |
| [Task 2]    | Name  | Medium   | Open   |

---

## 6. Root Cause Analysis (RCA) Template

### 1. What happened?
[High-level summary of the CLI failure.]

### 2. Why did it happen? (The "Why" Chain)
- **Problem:** [Symptom]
- **Cause 1:** [Direct cause] → Why? [Deeper reason]
- **Cause 2:** [Systemic cause] → Why? [Process failure]

### 3. Contributing Factors
- **Technical:** [e.g., Regressive change, missing OS compat check, broken dependency]
- **Process:** [e.g., Inadequate testing matrix, missed release checklist]
- **People:** [e.g., Communication gap with downstream tools]

### 4. Corrective Actions
- **Immediate:** [Actions taken to resolve (e.g., hotfix release)]
- **Short-term:** [Improve testing coverage for affected platform]
- **Long-term:** [Add regression gate to CI, canary releases]

### 5. Lessons Learned
[Key takeaways for the CLI development team.]
