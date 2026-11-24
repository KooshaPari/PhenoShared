# Release Matrix Template

Date: YYYY-MM-DD
Program: `name`
Channel: alpha|beta|rc|canary|release

| Task ID | Parent | PR Name | State | Depends | Risks | Gate | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | - | feat/...-alpha-core | alpha | - | low | pass | `owner` |
| 1.1 | 1 | feat/...-beta-cache | beta | 1 | med | pass | `owner` |
| 1.2 | 1 | feat/...-rc-renderer | rc | 1 | high | pass | `owner` |
