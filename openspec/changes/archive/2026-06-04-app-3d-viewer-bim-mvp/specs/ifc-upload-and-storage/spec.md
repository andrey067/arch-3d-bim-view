## ADDED Requirements

### Requirement: Accept IFC file upload
The system SHALL accept multipart form uploads containing a single `.ifc` file at `POST /api/projects/upload`.

#### Scenario: Successful upload
- **WHEN** a valid `.ifc` file under 500 MB is uploaded with a project name
- **THEN** the system stores the file in the `ifc-files` MinIO bucket, creates a `Project` record with status `Uploaded`, and returns a `201 Created` response with the project ID and metadata

#### Scenario: File exceeds size limit
- **WHEN** an `.ifc` file exceeding 500 MB is uploaded
- **THEN** the system returns `413 Payload Too Large` before fully buffering the request body

#### Scenario: Invalid file extension
- **WHEN** a file with an extension other than `.ifc` is uploaded
- **THEN** the system returns `400 Bad Request` with an error message indicating only `.ifc` files are accepted

#### Scenario: Missing project name
- **WHEN** the upload form does not include a `name` field
- **THEN** the system returns `400 Bad Request` with an error message indicating the name is required

### Requirement: Store original IFC in MinIO
The system SHALL store uploaded IFC files in the `ifc-files` MinIO bucket with a generated unique object key.

#### Scenario: IFC file stored successfully
- **WHEN** a valid IFC file is uploaded
- **THEN** the file is persisted to the `ifc-files` bucket with a key derived from the project ID and original filename, and the key is stored in the `Project` record's `IfcObjectKey` field

### Requirement: Validate file integrity
The system SHALL validate that the uploaded file is a well-formed IFC file by checking the IFC header.

#### Scenario: Corrupted or non-IFC file
- **WHEN** a file with `.ifc` extension but invalid IFC header is uploaded
- **THEN** the system returns `400 Bad Request` with a message indicating the file is not a valid IFC file

### Requirement: Configure MinIO buckets at startup
The system SHALL ensure the required MinIO buckets (`ifc-files`, `glb-files`, `thumbnails`) exist on application startup, creating them if necessary.

#### Scenario: Buckets created on first run
- **WHEN** the backend starts and any required bucket does not exist
- **THEN** the backend creates the missing buckets before accepting requests
