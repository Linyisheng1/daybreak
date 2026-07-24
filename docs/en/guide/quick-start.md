---
title: Quick Start
editLink: true
---

# Quick Start

The recommended deployment runs `daybreak.bin` on the Linux host, PostgreSQL under Compose, and project sandboxes as Docker containers managed dynamically by Daybreak. Python, Node.js, and local frontend builds are not required.

## Copy-Paste Install

Run this on an `x86_64/amd64` Linux host:

```bash
curl -fL --retry 3 -o daybreak-linux-amd64-v0.3.0.tar.gz \
  https://github.com/Linyisheng1/daybreak/releases/download/v0.3.0/daybreak-linux-amd64-v0.3.0.tar.gz
tar -xzf daybreak-linux-amd64-v0.3.0.tar.gz
cd daybreak-linux-amd64-v0.3.0

./daybreak doctor
./daybreak up
```

The Linux package supports `x86_64` systems with `glibc 2.31` or newer. Run
`ldd --version` to check the installed version. Do not replace the system glibc
manually just to run Daybreak.

If `curl` is not installed, first run the command for your distribution:

```bash
sudo apt-get update && sudo apt-get install -y curl  # Ubuntu / Debian
sudo dnf install -y curl                            # CentOS Stream / RHEL / Rocky / Alma
```

Open:

```text
http://SERVER_IP:8000
```

The default login is admin@daybreak.local with password admin. You can also verify it in .env:

```bash
grep -E "DAYBREAK_ADMIN_EMAIL|DAYBREAK_ADMIN_PASSWORD" .env
```

If `doctor` or `up` reports an environment issue, use the launcher helpers:

```bash
./daybreak install-docker     # Docker is not installed
./daybreak fix-permissions    # Current user cannot access Docker; sign in again afterwards
./daybreak registry-login     # Private GHCR image pull is denied
./daybreak status             # Inspect runtime status
./daybreak logs               # Inspect logs
```

## Requirements

| Item | Requirement |
| --- | --- |
| Operating system | Ubuntu, Debian, CentOS, RHEL, or compatible Linux |
| Architecture | `x86_64/amd64` |
| Container runtime | Docker Engine with Docker Compose v2 |
| Permission | The current user can read and write the Docker socket |
| Network | Access to Docker Hub, GHCR, and the configured model API |
| Suggested resources | 4 CPU cores, 8 GB RAM, and 20 GB free disk space |

The current sandbox image supports amd64 only. WSL2 with Docker integration is supported but not required.

## Release Layout

The extracted release should contain:

```text
daybreak.bin
daybreak
daybreak-defaults/
.env.example
deploy/docker-compose.dependencies.yml
```

Make the launcher and binary executable:

```bash
chmod +x daybreak daybreak.bin
```

## Preflight Check

```bash
./daybreak doctor
```

This command does not modify the host. It checks the Linux architecture, Docker CLI and API, Compose v2, Docker socket permission, and application binary.

### Docker is missing

For a quick evaluation installation, the launcher can invoke Docker's official convenience installer:

```bash
./daybreak install-docker
```

For production, install Docker from the official Ubuntu/Debian APT repository or CentOS/RHEL RPM repository instead.

### Docker permission is denied

```bash
./daybreak fix-permissions
```

Sign out of the Linux session and sign back in before running `./daybreak doctor` again. Do not expose an unauthenticated Docker API on TCP port 2375. Local Daybreak deployments use `/var/run/docker.sock`.

### GHCR access is denied

Public packages require no login. For a private GHCR package, run:

```bash
./daybreak registry-login
```

Enter a GitHub username and token with `read:packages`. The token is passed to Docker over standard input and is not stored in `.env`.

## First Start

```bash
./daybreak up
```

The launcher creates .env with mode 600, writes the default administrator login, generates deployment secrets, pulls PostgreSQL and the sandbox image, starts and validates PostgreSQL, synchronizes its password, starts daybreak.bin, initializes runtime files, registers the sandbox image, and waits for the HTTP health check.

Open:

```text
http://127.0.0.1:8000
```

The default administrator login is admin@daybreak.local / admin, stored in .env as DAYBREAK_ADMIN_EMAIL and DAYBREAK_ADMIN_PASSWORD.
Default image sources use China-friendly mirrors: docker.m.daocloud.io/postgres:16-alpine for PostgreSQL and ghcr.nju.edu.cn/linyisheng1/daybreak-sandbox:latest for the sandbox. To switch back to official sources, edit DAYBREAK_POSTGRES_IMAGE and DAYBREAK_SANDBOX_IMAGE in .env, then run ./daybreak restart.

## Model Configuration

Edit `.env`:

```dotenv
DAYBREAK_MODEL_BASE_URL=https://api.example.com/v1
DAYBREAK_MODEL_API_KEY=replace-with-your-api-key
DAYBREAK_MODEL_NAME=your-model-name
```

Apply the change:

```bash
./daybreak restart
```

The same `.env` supplies both PostgreSQL and Daybreak, so the database password is not maintained in two places. Model values override all bundled default agents at startup.

## Operations

```bash
./daybreak status
./daybreak logs
./daybreak restart
./daybreak down
```

`down` preserves the `daybreak-pgdata` volume. Do not run `docker compose down -v` unless permanent database deletion is intended.

## Persistent Data

| Data | Location |
| --- | --- |
| Deployment settings and secrets | `.env` |
| Daybreak configuration and agents | `.daybreak/` |
| Application log | `.daybreak/app.log` |
| PostgreSQL data | Docker volume `daybreak-pgdata` |
| Reports | `reports/` |
| Sandboxes | Docker containers created dynamically by Daybreak |

Back up `.env`, `.daybreak/`, `reports/`, and PostgreSQL before upgrades. Replacing `daybreak.bin` does not remove these locations.
## Upgrade

Use the launcher to update Daybreak without redeploying the database or pulling dependency images again:

```bash
./daybreak upgrade          # upgrade to the latest GitHub release
./daybreak upgrade 0.3.0    # upgrade to a specific release
```

The upgrade command keeps the current `.env`, PostgreSQL volume, reports, and local Docker images. It backs up replaced files under `.daybreak/backups/`, updates `daybreak.bin`, the launcher, dependency Compose, and default files, then restarts Daybreak if it was already running.

## Troubleshooting

- `Cannot connect to the Docker daemon`: start Docker, run `./daybreak fix-permissions`, then sign out and back in.
- `permission denied /var/run/docker.sock`: the current login session has not acquired Docker group membership.
- `unauthorized` or `denied`: make the GHCR package public or run `./daybreak registry-login` with a `read:packages` token.
- PostgreSQL failure: run `./daybreak logs`; check port 5432, disk capacity, and the existing data volume.
- UI works but sandboxes do not: run `./daybreak status` and verify both the sandbox image and Docker socket access.

## Next Step

After validating the model connection, follow [First Use](./first-use) to create a sandbox container and work project.
