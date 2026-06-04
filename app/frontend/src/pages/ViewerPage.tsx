import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { api, Project } from '../api/client';
import PropertiesPanel from '../components/PropertiesPanel';
import SpatialTree from '../components/SpatialTree';

interface ElementProperties {
  globalId?: string;
  type?: string;
  name?: string;
  description?: string;
  material?: string;
}

export default function ViewerPage() {
  const { id } = useParams<{ id: string }>();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const loaderRef = useRef<GLTFLoader | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedElement, setSelectedElement] = useState<ElementProperties | null>(null);
  const [showProperties, setShowProperties] = useState(true);
  const [showTree, setShowTree] = useState(true);
  const [sceneGraph, setSceneGraph] = useState<THREE.Object3D | null>(null);

  const initializeViewer = useCallback(() => {
    if (!canvasRef.current) return;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(
      60,
      canvasRef.current.clientWidth / canvasRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(5, 5, 5);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.current,
      antialias: true,
    });
    renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    rendererRef.current = renderer;

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controlsRef.current = controls;

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 10);
    scene.add(directionalLight);

    // Grid helper
    const gridHelper = new THREE.GridHelper(20, 20, 0xe2e8f0, 0xe2e8f0);
    scene.add(gridHelper);

    // Loader
    const loader = new GLTFLoader();
    loaderRef.current = loader;

    // Animation loop
    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Resize handler
    const handleResize = () => {
      if (!canvasRef.current || !camera || !renderer) return;
      camera.aspect = canvasRef.current.clientWidth / canvasRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      renderer.dispose();
    };
  }, []);

  const loadModel = useCallback((glbUrl: string) => {
    if (!loaderRef.current || !sceneRef.current) return;

    loaderRef.current.load(
      glbUrl,
      (gltf) => {
        const model = gltf.scene;
        sceneRef.current!.add(model);
        setSceneGraph(model);

        // Center camera on model
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const camera = cameraRef.current;
        if (camera) {
          camera.position.set(
            center.x + maxDim * 1.5,
            center.y + maxDim * 1.5,
            center.z + maxDim * 1.5
          );
          camera.lookAt(center);
        }
      },
      undefined,
      (err) => {
        console.error('Error loading GLB model:', err);
        setError('Failed to load 3D model');
      }
    );
  }, []);

  const handleCanvasClick = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current || !sceneRef.current || !cameraRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1
    );

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, cameraRef.current);

    const intersects = raycaster.intersectObjects(sceneRef.current.children, true);

    if (intersects.length > 0) {
      const selected = intersects[0].object;
      const properties: ElementProperties = {
        name: selected.name || selected.userData.name || 'Unnamed',
        type: selected.type || selected.userData.type || 'Object',
      };

      // Try to extract IFC metadata from userData
      if (selected.userData.globalId) {
        properties.globalId = selected.userData.globalId;
      }
      if (selected.userData.ifcType) {
        properties.type = selected.userData.ifcType;
      }
      if (selected.userData.description) {
        properties.description = selected.userData.description;
      }
      if (selected.userData.material) {
        properties.material = selected.userData.material;
      }

      setSelectedElement(properties);

      // Highlight selected object
      if (selected instanceof THREE.Mesh && selected.material) {
        const originalMaterial = selected.material;
        if (Array.isArray(originalMaterial)) {
          originalMaterial.forEach((mat) => {
            mat.emissive = new THREE.Color(0x2563eb);
            mat.emissiveIntensity = 0.3;
          });
        } else {
          originalMaterial.emissive = new THREE.Color(0x2563eb);
          originalMaterial.emissiveIntensity = 0.3;
        }
      }
    } else {
      setSelectedElement(null);
    }
  }, []);

  useEffect(() => {
    if (!id) return;

    const loadProject = async () => {
      setLoading(true);
      setError(null);
      try {
        const projectData = await api.getProject(id);
        setProject(projectData);

        // Initialize viewer after component mounts
        setTimeout(() => {
          initializeViewer();
        }, 0);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load project');
      } finally {
        setLoading(false);
      }
    };

    loadProject();
  }, [id, initializeViewer]);

  useEffect(() => {
    if (project?.glbUrl && loaderRef.current) {
      loadModel(project.glbUrl);
    }
  }, [project?.glbUrl, loadModel]);

  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      rendererRef.current?.dispose();
    };
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="skeleton" style={{ width: '200px', height: '200px', borderRadius: '50%', margin: '0 auto 1rem' }} />
          <div>Loading 3D viewer...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="error-message">{error}</div>
        <Link to="/" className="btn btn-secondary" style={{ marginTop: '1rem' }}>
          Back to Projects
        </Link>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <header className="header">
        <div className="header-title">
          {project?.name || 'BIM Viewer'}
        </div>
        <nav className="header-nav">
          <Link to="/" className="btn btn-secondary">
            Projects
          </Link>
          {project && (
            <Link to={`/share/${project.id}/ar`} className="btn btn-primary">
              View in AR
            </Link>
          )}
        </nav>
      </header>

      {/* Main Content */}
      <div className="viewer-layout">
        {/* Spatial Tree Panel */}
        {showTree && (
          <div className="viewer-panel" style={{ borderRight: '1px solid var(--border-color)', borderLeft: 'none' }}>
            <div className="panel-header">
              <span>Spatial Tree</span>
              <span className="panel-toggle" onClick={() => setShowTree(false)}>
                ✕
              </span>
            </div>
            <div className="panel-content">
              <SpatialTree sceneGraph={sceneGraph} onSelect={(obj) => setSelectedElement(obj)} />
            </div>
          </div>
        )}

        {/* 3D Canvas */}
        <div className="viewer-main">
          {!showTree && (
            <button
              className="btn btn-secondary"
              style={{ position: 'absolute', top: '1rem', left: '1rem', zIndex: 10 }}
              onClick={() => setShowTree(true)}
            >
              Show Tree
            </button>
          )}
          <canvas
            ref={canvasRef}
            className="viewer-canvas"
            onClick={handleCanvasClick}
          />
        </div>

        {/* Properties Panel */}
        {showProperties && (
          <div className="viewer-panel">
            <div className="panel-header">
              <span>Properties</span>
              <span className="panel-toggle" onClick={() => setShowProperties(false)}>
                ✕
              </span>
            </div>
            <div className="panel-content">
              <PropertiesPanel element={selectedElement} />
            </div>
          </div>
        )}

        {/* Toggle Properties Button */}
        {!showProperties && (
          <button
            className="btn btn-secondary"
            style={{ position: 'absolute', top: '1rem', right: '1rem', zIndex: 10 }}
            onClick={() => setShowProperties(true)}
          >
            Show Properties
          </button>
        )}
      </div>
    </div>
  );
}
