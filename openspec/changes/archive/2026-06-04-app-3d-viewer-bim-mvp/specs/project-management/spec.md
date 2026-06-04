## ADDED Requirements

### Requirement: List all projects
The system SHALL return a paginated list of all projects via `GET /api/projects`.

#### Scenario: Empty project list
- **WHEN** no projects have been uploaded
- **THEN** the endpoint returns an empty array with `200 OK`

#### Scenario: Projects with metadata
- **WHEN** projects exist in the database
- **THEN** the endpoint returns each project's `id`, `name`, `description`, `status`, `thumbnailUrl`, and `createdAt`

### Requirement: Get project details
The system SHALL return full project details including storage keys and conversion status via `GET /api/projects/{id}`.

#### Scenario: Existing project
- **WHEN** a valid project ID is requested
- **THEN** the endpoint returns the project's `id`, `name`, `description`, `status`, `ifcObjectKey`, `glbObjectKey`, `thumbnailObjectKey`, `shareUrl`, and `createdAt`

#### Scenario: Non-existent project
- **WHEN** an invalid or non-existent project ID is requested
- **THEN** the endpoint returns `404 Not Found`

### Requirement: Create project on upload
The system SHALL create a `Project` database record when an IFC file is uploaded, with the provided name and optional description.

#### Scenario: Project created with name
- **WHEN** an IFC file is uploaded with `name: "Residencial Villa"`
- **THEN** a new `Project` record is created with `Name = "Residencial Villa"` and a generated GUID as `Id`

### Requirement: Generate presigned URLs for storage access
The system SHALL generate time-limited presigned URLs for IFC, GLB, and thumbnail objects so the frontend can access them without direct MinIO credentials.

#### Scenario: Presigned URL generated
- **WHEN** the frontend requests a project's GLB file
- **THEN** the backend generates a presigned GET URL for the `glb-files` object with a 1-hour expiry and returns it in the response
