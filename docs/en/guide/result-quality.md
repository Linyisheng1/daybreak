---
title: Result Quality
editLink: true
---

# Result Quality

Daybreak agents, methodology skills, and sandbox tools help security professionals collect leads, reproduce issues, and preserve evidence. Automated output is not a final vulnerability verdict. A version string, response header, error page, or scanner template match alone must not be treated as a confirmed high-severity issue.

## Finding Status

| Status | Meaning | Included in confirmed risk totals |
| --- | --- | --- |
| `suspected` | A useful lead whose evidence or impact is incomplete | No |
| `validated` | Reproduced with confirmed security impact | Yes |
| `false_positive` | Reviewed and ruled out | No |

The current release does not enforce every evidence rule on the server. Operators must review status and severity before delivering a report.

## Minimum Validation Standard

A confirmed finding should include:

1. The affected asset, entry point, parameter, and authentication conditions.
2. Steps another tester can repeat.
3. Raw evidence such as a request and response, command output, screenshot, or file.
4. Demonstrated impact rather than theoretical risk alone.
5. Checks that rule out caching, permission differences, network failures, and tool false positives.

High and critical findings should be reproduced a second time and, where practical, independently reviewed by another operator or agent.

## Severity Baseline

| Severity | Reference condition |
| --- | --- |
| Informational/Low | Exposure or weak configuration without demonstrated direct impact |
| Medium | Reproduced impact limited to one user, a small data set, or a local feature |
| High | Demonstrated authorization bypass, sensitive data access, account takeover, file access, or internal reachability |
| Critical | Demonstrated low-friction large-scale compromise, remote code execution, core data exposure, or a decisive attack-chain step |

A scanner hit, component version, or public CVE match should remain suspected until it is validated against the actual target.

## Before Exporting a Report

- Every high or critical item is `validated`.
- Every validated item contains raw evidence and demonstrated impact.
- Duplicate findings are merged and their evidence is consolidated.
- Suspected leads are separated from confirmed vulnerabilities.
- Tool runs produced meaningful output, not only a successful exit code.
- Credentials, personal information, and customer data are redacted.

## Sandbox Capabilities

Methodology skills describe workflows; sandbox images provide execution capabilities. The presence of a skill does not guarantee that a matching command is installed. Verify required commands or browser capabilities before execution. Missing tools, empty output, or runtime failures should be recorded as blockers, never as evidence that confirms a vulnerability.
