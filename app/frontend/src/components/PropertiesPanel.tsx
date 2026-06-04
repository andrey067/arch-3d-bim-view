import React from 'react';

interface ElementProperties {
  globalId?: string;
  type?: string;
  name?: string;
  description?: string;
  material?: string;
}

interface PropertiesPanelProps {
  element: ElementProperties | null;
}

export default function PropertiesPanel({ element }: PropertiesPanelProps) {
  if (!element) {
    return (
      <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
        <p>Select an element to view its properties</p>
      </div>
    );
  }

  const properties = [
    { label: 'Name', value: element.name },
    { label: 'Type', value: element.type },
    { label: 'Global ID', value: element.globalId },
    { label: 'Material', value: element.material },
    { label: 'Description', value: element.description },
  ].filter((prop) => prop.value);

  return (
    <div>
      {properties.map((prop) => (
        <div key={prop.label} className="property-row">
          <span className="property-label">{prop.label}</span>
          <span className="property-value">{prop.value}</span>
        </div>
      ))}
    </div>
  );
}
