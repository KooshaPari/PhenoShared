# Testing and Evidence Strategy

This packet needs documentation-link validation only. Before publication or a coordinated readiness claim, reviewers need exact evidence:

| Surface        | Owner                | Required evidence                                                                                                                                                          |
| -------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ResearchLedger | ResearchLedger owner | Exact inventory commit `8822aa14baef2a964288076645edcc493c338688`, registry link resolves to that commit, commands/results, and review. Record any remote head separately. |
| Benchora       | Benchora owner       | Hosted artifact commit/path, #107 head, scorecard, Sonar, and Infisical disposition.                                                                                       |
| Registry links | Registry reviewer    | Local-vs-remote wording matches owner evidence; no catalog/schema mutation.                                                                                                |

Do not run APIs, corpus acquisition, CI dispatch, or scanners for registry routing validation.
