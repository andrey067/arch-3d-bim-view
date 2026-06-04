## ADDED Requirements

### Requirement: Docker Compose orchestration
The system SHALL be deployable via a single `docker-compose.yml` file that defines all required services.

#### Scenario: All services start with docker compose up
- **WHEN** `docker compose up -d` is executed in the project root
- **THEN** all six services (postgres, minio, backend, frontend, converter, nginx) start and become healthy

### Requirement: Service definitions
The Docker Compose file SHALL define the following services with appropriate configurations:

| Service    | Image / Build         | Ports        | Dependencies       |
|------------|----------------------|-------------|---------------------|
| postgres   | postgres:16-alpine   | 5432        | —                   |
| minio      | minio/minio:latest   | 9000, 9001  | —                   |
| backend    | build: ./backend     | 5000        | postgres, minio     |
| frontend   | build: ./frontend    | 3000        | backend             |
| converter  | build: ./converter   | —           | minio               |
| nginx      | nginx:alpine         | 80, 443     | frontend, backend   |

#### Scenario: Service health checks
- **WHEN** Docker Compose starts the stack
- **THEN** each service has a configured health check, and dependent services wait for healthy status before starting

### Requirement: nginx reverse proxy
The nginx service SHALL reverse proxy requests to the frontend (static files + SPA routing) and backend (API endpoints).

#### Scenario: API request routed to backend
- **WHEN** a request hits `/api/*`
- **THEN** nginx proxies it to the backend service on port 5000

#### Scenario: Frontend routes served by SPA
- **WHEN** a request hits any route not matching `/api/*` or `/share/*`
- **THEN** nginx serves the frontend static files with SPA fallback (`try_files $uri /index.html`)

### Requirement: Volume persistence
The Docker Compose configuration SHALL use named volumes for PostgreSQL data and MinIO data to survive container restarts.

#### Scenario: Data persists across container recreation
- **WHEN** containers are stopped and restarted
- **THEN** all database records and stored files in MinIO are preserved

### Requirement: Environment configuration
The system SHALL use a `.env` file for configurable values (database credentials, MinIO access keys, bucket names) with sensible defaults for development.

#### Scenario: Configuration via .env file
- **WHEN** the `.env` file is present in the project root
- **THEN** Docker Compose reads values from it, overriding the defaults in `docker-compose.yml`

### Requirement: Kubernetes readiness
The architecture SHALL be structured for future migration to Kubernetes: stateless application containers, externalized storage (MinIO, PostgreSQL), health check endpoints, and no hardcoded hostnames between services.

#### Scenario: Services use service discovery
- **WHEN** the backend needs to connect to PostgreSQL or MinIO
- **THEN** it uses environment variables for host/port/credentials rather than hardcoded values

### Requirement: File upload size configuration
The nginx service SHALL be configured with `client_max_body_size 500m` to accept large IFC file uploads.

#### Scenario: Large file upload passes through nginx
- **WHEN** a 500 MB IFC file is uploaded via the frontend
- **THEN** nginx does not reject the request body
