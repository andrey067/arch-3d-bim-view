## ADDED Requirements

### Requirement: Render GLB in AR using model-viewer
The AR viewer SHALL load the GLB model using Google's `<model-viewer>` web component and support augmented reality viewing.

#### Scenario: AR viewer page loads
- **WHEN** the AR viewer page is opened with a valid GLB presigned URL
- **THEN** the `<model-viewer>` component renders the 3D model with camera controls and an "View in AR" button

### Requirement: Support Android AR via Scene Viewer
The AR viewer SHALL support AR mode on Android devices using Scene Viewer (`ar-modes="scene-viewer"`).

#### Scenario: AR launched on Android
- **WHEN** a user on an Android device with ARCore support taps "View in AR"
- **THEN** Scene Viewer launches and displays the model in the real-world environment

### Requirement: Support iOS AR via Quick Look
The AR viewer SHALL support AR mode on iOS devices using Quick Look (`ar-modes="quick-look"`).

#### Scenario: AR launched on iOS
- **WHEN** a user on an iOS device with ARKit support taps "View in AR"
- **THEN** Quick Look launches and displays the model in the real-world environment

### Requirement: WebXR fallback
The AR viewer SHALL include WebXR as a fallback AR mode for browsers that support the WebXR Device API.

#### Scenario: WebXR fallback
- **WHEN** a user is on a device that supports WebXR but not Scene Viewer or Quick Look
- **THEN** the AR experience launches inline in the browser using the WebXR session

### Requirement: AR viewer accessible from BIM viewer
The AR viewer page SHALL be accessible via a "View in AR" button from the BIM viewer page.

#### Scenario: Navigate from BIM viewer to AR
- **WHEN** a user clicks "View in AR" on the BIM viewer page
- **THEN** the browser navigates to `/share/{id}/ar` which renders the AR viewer with the same GLB model

### Requirement: HTTPS required for AR
The AR viewer SHALL only function over HTTPS connections, as required by browser AR APIs.

#### Scenario: AR blocked on HTTP
- **WHEN** the AR viewer is loaded over HTTP
- **THEN** the "View in AR" button is disabled with a message: "AR requires a secure connection (HTTPS)"
