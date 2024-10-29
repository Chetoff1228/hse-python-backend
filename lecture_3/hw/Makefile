# Makefile for FastAPI, Prometheus, and Grafana

# Variables
COMPOSE_FILE = docker-compose.yml

# Default target
.PHONY: all
all: build up

# Build the Docker images
.PHONY: build
build:
	docker-compose -f $(COMPOSE_FILE) build

# Start the services
.PHONY: up
up:
	docker-compose -f $(COMPOSE_FILE) up

# Stop the services
.PHONY: down
down:
	docker-compose -f $(COMPOSE_FILE) down

# Show logs
.PHONY: logs
logs:
	docker-compose -f $(COMPOSE_FILE) logs -f

# Clean up volumes
.PHONY: clean
clean:
	docker-compose -f $(COMPOSE_FILE) down -v

# Execute a shell in the FastAPI service
.PHONY: shell
shell:
	docker-compose -f $(COMPOSE_FILE) exec fastapi /bin/sh
