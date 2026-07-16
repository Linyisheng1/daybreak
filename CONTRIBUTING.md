# Contributing to Daybreak

Thank you for helping improve Daybreak. Contributions to code, documentation, tests, sandbox images, and methodology skills are welcome.

## Before You Start

- Open an issue for large architectural changes before implementation.
- Keep changes focused and avoid unrelated formatting or generated-file churn.
- Never commit API keys, passwords, access tokens, customer data, or assessment evidence.
- Use only targets and test data that you are authorized to access.

## Development Checks

Backend syntax check:

```bash
python -m compileall -q app.py config.py database.py logger.py main.py core handler middleware model router schema service utils
```

Frontend checks:

```bash
cd web
npm ci
npm run typecheck
npm run build
```

Documentation check:

```bash
cd docs
npm ci
npm run docs:build
```

Add focused tests when changing authentication, authorization, project records, sandbox lifecycle, command execution, or report generation.

## Finding Quality

Changes that create or transform security findings must preserve the distinction between a lead and a confirmed vulnerability.

- Scanner output and version matches start as `suspected`.
- A `validated` finding needs reproducible evidence and demonstrated impact.
- High and critical severity require stronger proof than descriptive text.
- Reports must keep suspected leads separate from confirmed risk totals.
- Empty command output or a successful exit code alone is not evidence.

See [Result Quality](docs/en/guide/result-quality.md) for the full baseline.

## Sandbox and Skill Contributions

- A skill should describe a reusable workflow, its assumptions, and its required capabilities.
- Do not claim that a tool is available unless the image installs and verifies it.
- Missing optional tools must fail clearly; do not replace them with successful no-op scripts.
- Keep the base image small and place specialized capabilities in dedicated images where practical.
- Document network downloads, supported architectures, and version pins.

## Pull Requests

A pull request should include:

- a concise problem statement;
- the behavioral change and affected components;
- verification performed;
- screenshots for visible frontend changes;
- migration or deployment notes when configuration or stored data changes.

By contributing, you agree that your contribution is licensed under the repository's MIT License.
