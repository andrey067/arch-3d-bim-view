## ADDED Requirements

### Requirement: Generate thumbnail during conversion
The system SHALL generate a PNG thumbnail image of the IFC model during the conversion process.

#### Scenario: Thumbnail generated on successful conversion
- **WHEN** the IFC-to-GLB conversion completes successfully
- **THEN** a PNG thumbnail (at least 512px on the longest edge) is generated and stored in the `thumbnails` MinIO bucket

#### Scenario: Thumbnail generation failure is non-blocking
- **WHEN** the thumbnail generation step fails but GLB conversion succeeded
- **THEN** the project status remains `Completed`, a placeholder thumbnail is used, and the error is logged

### Requirement: Store thumbnail in MinIO
The system SHALL store generated thumbnails in the `thumbnails` MinIO bucket and update the project's `ThumbnailObjectKey`.

#### Scenario: Thumbnail stored and linked
- **WHEN** a thumbnail is generated
- **THEN** the PNG file is uploaded to the `thumbnails` bucket, the `ThumbnailObjectKey` in the `Project` record is updated, and the thumbnail is accessible via a presigned URL

### Requirement: Display thumbnail in project list
The frontend SHALL display thumbnails in the projects list page.

#### Scenario: Thumbnail shown in project list
- **WHEN** the projects list page loads
- **THEN** each project card displays its thumbnail image (or a placeholder if thumbnail is unavailable)

### Requirement: Thumbnail as social preview
The system SHALL use the project thumbnail as the Open Graph image for the share page, enabling rich link previews when shared on social media or messaging apps.

#### Scenario: Open Graph image set
- **WHEN** the share page at `/share/{id}` is rendered
- **THEN** the HTML includes `<meta property="og:image" content="{thumbnailUrl}">`
