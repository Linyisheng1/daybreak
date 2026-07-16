# Docker deployment files

The recommended end-user deployment runs `daybreak.bin` on the Linux host and uses [`deploy/docker-compose.dependencies.yml`](../deploy/docker-compose.dependencies.yml) for PostgreSQL and the sandbox image dependency.

Run deployment commands from the repository or release root:

```bash
./daybreak doctor
./daybreak up
./daybreak status
./daybreak logs
./daybreak down
```

`docker/docker-compose.yml` and `docker/Dockerfile` remain available for developers who need to build and run the application itself as a container. They are not the recommended binary release path and must not be used together with the same `daybreak-postgres` container managed by the binary deployment.

The dependency deployment stores PostgreSQL data in the `daybreak-pgdata` Docker volume. Sandbox containers are created dynamically by Daybreak and are intentionally not declared as long-running Compose services.
