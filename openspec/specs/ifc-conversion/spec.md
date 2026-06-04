## ADDED Requirements

### Requirement: Trigger conversion on new IFC upload
The system SHALL initiate an asynchronous IFC-to-GLB conversion when a new IFC file is successfully uploaded and stored.

#### Scenario: Conversion triggered after upload
- **WHEN** an IFC file is uploaded and persisted to MinIO
- **THEN** the project status transitions to `Queued` and a conversion job is dispatched to the converter service

### Requirement: Convert IFC to GLB using IfcConvert
The converter service SHALL execute `IfcConvert` with the input IFC file and produce a valid GLB output file.

#### Scenario: Successful conversion
- **WHEN** IfcConvert processes a valid IFC file
- **THEN** a GLB file is produced and stored in the `glb-files` MinIO bucket, and the project status transitions to `Completed`

#### Scenario: Conversion failure
- **WHEN** IfcConvert encounters an unrecoverable error (malformed IFC, unsupported geometry)
- **THEN** the project status transitions to `Failed` with an error message recorded, and no GLB file is stored

### Requirement: Poll conversion status
The system SHALL expose the project's conversion status via `GET /api/projects/{id}` so the frontend can display progress.

#### Scenario: Status returned in project details
- **WHEN** the frontend requests project details
- **THEN** the response includes a `status` field with one of: `Uploaded`, `Queued`, `Processing`, `Completed`, or `Failed`

### Requirement: Store GLB in MinIO
The converter service SHALL store the output GLB file in the `glb-files` MinIO bucket with a key derived from the project ID.

#### Scenario: GLB stored after conversion
- **WHEN** IfcConvert completes successfully
- **THEN** the GLB file is uploaded to the `glb-files` bucket, and the `GlbObjectKey` field in the `Project` record is updated

### Requirement: Converter runs in isolated container
The converter service SHALL run as a separate Docker container with access to the MinIO instance and the IfcConvert binary.

#### Scenario: Converter container starts
- **WHEN** Docker Compose brings up the stack
- **THEN** the converter service is running, IfcConvert is on PATH, and the service can connect to MinIO
