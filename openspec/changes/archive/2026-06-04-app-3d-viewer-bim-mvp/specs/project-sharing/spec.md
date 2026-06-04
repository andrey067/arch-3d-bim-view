## ADDED Requirements

### Requirement: Generate shareable public URL
The system SHALL generate a unique, public share URL for each project in the format `/share/{projectId}`.

#### Scenario: Share URL generated on project creation
- **WHEN** a project is created from an IFC upload
- **THEN** a `shareUrl` is generated and stored in the `Project` record

### Requirement: Serve BIM viewer at share URL
The system SHALL serve the BIM viewer page at `GET /share/{id}` with no authentication required.

#### Scenario: Viewer loaded via share link
- **WHEN** anyone opens `/share/{projectId}` in a browser
- **THEN** the BIM viewer page loads with the project's GLB model and properties

#### Scenario: Invalid share link
- **WHEN** a non-existent project ID is accessed via `/share/{invalidId}`
- **THEN** the system returns a "Project not found" page with `404` status

### Requirement: Serve AR viewer at share URL
The system SHALL serve the AR viewer page at `GET /share/{id}/ar` with no authentication required.

#### Scenario: AR viewer loaded via share link
- **WHEN** anyone opens `/share/{projectId}/ar` on a mobile device
- **THEN** the AR viewer page loads with the project's GLB model ready for AR viewing

### Requirement: Share links are unguessable
The system SHALL use randomly generated GUIDs as project IDs to make share URLs unguessable.

#### Scenario: GUID format for project IDs
- **WHEN** a project is created
- **THEN** its ID is a Version 4 UUID (36-character hexadecimal string with dashes)

### Requirement: Share page displays project metadata
The share page SHALL display the project name, description, and creation date alongside the viewer.

#### Scenario: Metadata shown on share page
- **WHEN** a share link is opened
- **THEN** the page header displays the project name, optional description, and upload date
