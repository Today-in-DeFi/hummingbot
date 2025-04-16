# Docker Usage Guide

## 1. Introduction
This guide provides instructions for developers and analysts on how to run and manage the Hummingbot container using Docker. It includes a Makefile for automating common tasks.

> [!IMPORTANT]
> Working directory on our DigitalOcean droplet:
> `/home/jacques/hummingbot-tid`

## 2. Prerequisites
- Ensure Docker and Docker Compose are installed on your system.
- Familiarize yourself with basic Docker commands.

## 3. Recommended Workflow

### 3.1 Local Development & Testing
1. Edit or create strategy scripts in the local `scripts/` directory.
2. Start the container (using the official image):
   ```bash
   make up
   # or
   docker compose up -d
   ```
3. Attach to the Hummingbot CLI for interactive operations:
   ```bash
   make cli
   # or
   docker attach hummingbot
   ```
   - To detach without stopping the container, use `Ctrl-p` then `Ctrl-q`.
   - **Do not use `exit` or `quit` in the CLI unless you want to stop the container.**
4. When you update scripts in `scripts/`, simply restart the container to load changes:
   ```bash
   docker compose restart
   # or
   make down && make up
   ```
5. If you do NOT change code, you can safely detach/attach the CLI multiple times without restarting the container. All state will be preserved.

### 3.2 Production Deployment (Remote VM)
1. Sync your updated `scripts/` to the VM (via git, scp, or rsync).
2. Ensure the `docker-compose.yml` on the VM uses the official image and mounts the correct directories.
3. Start or restart the container as needed:
   ```bash
   docker compose up -d
   docker compose restart
   ```
4. Attach to the CLI for monitoring or control.

### 3.3 Maintenance & Best Practices
- Only restart the container if you modify code or configuration files mounted into the container (e.g., `scripts/`).
- To keep the bot running, always detach from the CLI using `Ctrl-p` then `Ctrl-q`.
- Use `docker compose logs -f` or `make logs` to monitor logs without entering the CLI.



## 4. Docker Commands

> [!NOTE]
> Make sure that you're at `/home/jacques/hummingbot-tid`.

### 4.1 Running the Container
To start the container in detached mode, run:
```bash
docker compose up -d
# or
make up
```


### 4.2 Stopping the Container
To stop the running container, use:
```bash
docker compose down
# or
make down
```

### 4.3 Checking Container Status
To check if the container is running, use:
```bash
docker ps
```

### 4.4 Interactive Access
To access the container interactively, you have two options:

#### 4.4.1 Attach to the Hummingbot CLI interface
```bash
docker attach hummingbot
# or
make cli
```
This will attach your terminal directly to the Hummingbot CLI running inside the container.

> [!IMPORTANT]
> If you type `exit` or `quit` in the Hummingbot CLI, it will stop the Hummingbot process and the Docker container will also stop. To leave the CLI without stopping the container, press `Ctrl-p` then `Ctrl-q` to detach safely.

#### 4.4.2 Open a Bash shell inside the container
```bash
docker exec -it hummingbot /bin/bash
```
This gives you a shell prompt for advanced debugging or file operations.


### 4.5 Restarting the Container
To restart the container, use:
```bash
docker compose restart
```

**Note:** If you have not modified the `scripts/` directory or other mounted code files, you usually do not need to restart the container. Simply detach from the CLI (using `Ctrl-p` then `Ctrl-q`) and re-attach (`docker attach hummingbot` or `make cli`) when needed. See . The container and its internal state will remain unchanged.



### 4.6 Building the Image
To build the image, one may use:
```bash
make build
```

> [!NOTE]
> For most development and testing needs, it is NOT necessary to build the Docker image locally.
> We recommend using the official Docker image and mounting your local scripts or configuration as Docker volumes. This approach allows you to:
> - Avoid long build times and potential build errors.
> - Instantly test changes to scripts without rebuilding the image.
> - Ensure consistency between local and production environments.
>
> **Only build the image locally if you need to modify the core source code or dependencies that are not covered by the official image.**


## 5. Makefile
Below is the Makefile to automate the above tasks:

```makefile
.PHONY: up down logs cli

up:
    docker compose up -d

down:
    docker compose down

logs:
    docker compose logs -f

cli:
    docker attach hummingbot
```
