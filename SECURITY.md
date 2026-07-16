# Security Policy

## Supported Versions

Daybreak is under active development. Security fixes are applied to the latest `main` branch and the latest published release. Older revisions may not receive backports.

## Reporting a Vulnerability

Please do not open a public issue for a vulnerability that could expose users, credentials, deployment infrastructure, or sandbox escape paths.

Use GitHub's private vulnerability reporting for this repository:

https://github.com/Linyisheng1/daybreak/security/advisories/new

Include, where available:

- the affected commit or release;
- the affected component and deployment mode;
- reproduction steps and minimal evidence;
- expected impact and required preconditions;
- suggested mitigation or patch direction.

Remove API keys, access tokens, customer data, and unrelated target information from the report. Please allow time for validation and remediation before public disclosure.

## Deployment Security

Daybreak controls Docker hosts and sandbox containers and may mount `/var/run/docker.sock`. Treat the application as a high-privilege administrative service.

Before exposing it beyond a local evaluation environment:

- replace all example administrator and database credentials;
- generate a unique `system.encrypt_key`;
- place the service behind TLS and access controls;
- restrict access to trusted operators and networks;
- isolate the Docker host from unrelated production workloads;
- back up PostgreSQL and runtime configuration before upgrades;
- review sandbox egress policies and generated artifacts.

Only use Daybreak against systems for which you have explicit authorization.
