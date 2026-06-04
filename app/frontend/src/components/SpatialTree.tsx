import { useState } from 'react';
import * as THREE from 'three';

interface SpatialTreeProps {
  sceneGraph: THREE.Object3D | null;
  onSelect: (properties: Record<string, string | undefined>) => void;
}

interface TreeNodeProps {
  object: THREE.Object3D;
  depth: number;
  onSelect: (properties: Record<string, string | undefined>) => void;
}

function TreeNode({ object, depth, onSelect }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(depth < 2);
  const hasChildren = object.children.length > 0;
  const nodeLabel = object.name || object.userData.name || `${object.type} (${object.children.length})`;

  const handleSelect = () => {
    onSelect({
      name: object.name || object.userData.name || 'Unnamed',
      type: object.userData.ifcType || object.type || 'Object',
      globalId: object.userData.globalId,
      material: object.userData.material,
      description: object.userData.description,
    });
  };

  return (
    <div>
      <div
        className="tree-item"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={handleSelect}
      >
        {hasChildren && (
          <span
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            style={{ cursor: 'pointer', marginRight: '4px' }}
          >
            {isExpanded ? '▼' : '▶'}
          </span>
        )}
        {!hasChildren && <span style={{ marginRight: '18px' }}>•</span>}
        <span>{nodeLabel}</span>
      </div>
      {isExpanded && hasChildren && (
        <div className="tree-children">
          {object.children.map((child, index) => (
            <TreeNode
              key={`${child.uuid}-${index}`}
              object={child}
              depth={depth + 1}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function SpatialTree({ sceneGraph, onSelect }: SpatialTreeProps) {
  if (!sceneGraph) {
    return (
      <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
        <p>Loading spatial tree...</p>
      </div>
    );
  }

  return (
    <div>
      <TreeNode object={sceneGraph} depth={0} onSelect={onSelect} />
    </div>
  );
}
