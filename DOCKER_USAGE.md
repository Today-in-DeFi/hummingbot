# Docker Usage Guide for Developers and Analysts

## Introduction
This guide provides instructions for developers and analysts on how to build, run, and manage the Hummingbot container using Docker. It includes a Makefile for automating common tasks.

## Prerequisites
- Ensure Docker and Docker Compose are installed on your system.
- Familiarize yourself with basic Docker commands.

## For Developers

### Building the Docker Image
To build the Docker image locally, execute the following command:
```bash
make build
```
This uses the `docker-compose.yml` configuration to build the image from the Dockerfile.

### Running the Container
To start the container in detached mode, run:
```bash
make up
```

### Stopping the Container
To stop the running container, use:
```bash
make down
```

### Viewing Logs
To view the logs of the running container, execute:
```bash
make logs
```

## For Analysts

### Starting the Container
Ensure the container is built and then start it using:
```bash
make up
```

### Stopping the Container
When analysis is complete, stop the container with:
```bash
make down
```

### Checking Container Status
To check if the container is running, use:
```bash
docker ps
```

## Makefile
Below is the Makefile to automate the above tasks:

```makefile
.PHONY: build up down logs

build:
	docker-compose build

up:
	docker-compose up -d

logs:
	docker-compose logs -f

stop:
	docker-compose down
```
