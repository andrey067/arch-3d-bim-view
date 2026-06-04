## ADDED Requirements

### Requirement: Load and render GLB model
The BIM viewer SHALL load a GLB model from a presigned URL and render it in a WebGL canvas using That Open Components.

#### Scenario: Model loads successfully
- **WHEN** the viewer page receives a valid GLB presigned URL
- **THEN** the 3D model is rendered in the viewport with default camera position framing the entire model

#### Scenario: Model fails to load
- **WHEN** the GLB URL is invalid or expired
- **THEN** the viewer displays an error message: "Failed to load model. The link may have expired."

### Requirement: Camera controls
The viewer SHALL support orbit (rotate around a point), pan (translate view), and zoom (dolly in/out) camera interactions.

#### Scenario: User orbits the model
- **WHEN** the user clicks and drags with the left mouse button
- **THEN** the camera orbits around the current focal point

#### Scenario: User pans the view
- **WHEN** the user clicks and drags with the right mouse button (or middle button)
- **THEN** the camera translates perpendicular to the view direction

#### Scenario: User zooms in
- **WHEN** the user scrolls the mouse wheel forward
- **THEN** the camera moves closer to the focal point

### Requirement: Element selection
The viewer SHALL allow the user to click on individual IFC elements to select them, highlighting the selected element.

#### Scenario: Single element selected
- **WHEN** the user clicks on a wall element in the 3D view
- **THEN** the wall is visually highlighted (outline or color change) and its IFC properties are displayed in the properties panel

#### Scenario: Click empty space deselects
- **WHEN** the user clicks on empty space in the viewport
- **THEN** the current selection is cleared and the properties panel resets

### Requirement: Display IFC properties
The viewer SHALL display IFC properties (GlobalId, type, name, dimensions, material, and classification) of the selected element in a side panel.

#### Scenario: Properties displayed for selected element
- **WHEN** a user selects an IFC element
- **THEN** the properties panel shows: GlobalId, IFC type (e.g., IfcWall), Name, Description, and relevant quantities (length, area, volume if available)

### Requirement: Spatial tree navigation
The viewer SHALL display a hierarchical spatial tree of the IFC model showing the project structure (Site → Building → Storey → Elements).

#### Scenario: Spatial tree rendered
- **WHEN** the model loads
- **THEN** a tree panel shows the hierarchical structure with expandable/collapsible nodes

#### Scenario: Click tree node selects element
- **WHEN** the user clicks an element node in the spatial tree
- **THEN** the corresponding element is selected and highlighted in the 3D view, and the camera flies to frame it

### Requirement: IFC classification display
The viewer SHALL display the IFC classification (IfcWall, IfcSlab, IfcWindow, etc.) for each element in both the spatial tree and the properties panel.

#### Scenario: Classification visible in tree
- **WHEN** the spatial tree is rendered
- **THEN** each element node shows its IFC class name alongside the element name

### Requirement: Loading state
The viewer SHALL display a loading indicator while the GLB model is being fetched and parsed.

#### Scenario: Loading spinner during model fetch
- **WHEN** the viewer page starts loading a GLB model
- **THEN** a loading spinner or progress indicator is displayed until the model is fully rendered
