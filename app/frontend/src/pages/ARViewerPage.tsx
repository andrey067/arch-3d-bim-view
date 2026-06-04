import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, ShareData } from '../api/client';

export default function ARViewerPage() {
  const { id } = useParams<{ id: string }>();
  const [shareData, setShareData] = useState<ShareData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isHTTPS, setIsHTTPS] = useState(true);

  useEffect(() => {
    // Check if we're on HTTPS
    setIsHTTPS(window.location.protocol === 'https:');

    if (!id) return;

    const loadShareData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getShareData(id);
        setShareData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load project');
      } finally {
        setLoading(false);
      }
    };

    loadShareData();
  }, [id]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="skeleton" style={{ width: '200px', height: '200px', borderRadius: '50%', margin: '0 auto 1rem' }} />
          <div>Loading AR viewer...</div>
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

  const handleARView = () => {
    const modelViewer = document.querySelector('model-viewer');
    if (modelViewer) {
      // @ts-ignore
      modelViewer.activateAR();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <header className="header">
        <div className="header-title">
          {shareData?.projectName || 'AR Viewer'}
        </div>
        <nav className="header-nav">
          <Link to={`/share/${id}`} className="btn btn-secondary">
            Back to Viewer
          </Link>
        </nav>
      </header>

      {/* HTTPS Warning */}
      {!isHTTPS && (
        <div
          style={{
            background: '#fef3c7',
            border: '1px solid #f59e0b',
            color: '#92400e',
            padding: '1rem',
            textAlign: 'center',
          }}
        >
          ⚠️ AR viewing requires HTTPS. Please access this page via a secure connection.
        </div>
      )}

      {/* Model Viewer */}
      {shareData?.glbUrl && (
        <div style={{ flex: 1, position: 'relative' }}>
          {/* @ts-ignore */}
          <model-viewer
            src={shareData.glbUrl}
            ar
            ar-modes="webxr scene-viewer quick-look"
            camera-controls
            autoplay
            style={{
              width: '100%',
              height: 'calc(100vh - 60px)',
              background: '#f8fafc',
            }}
          />

          {/* AR Button Overlay */}
          <button
            className="btn btn-primary"
            style={{
              position: 'absolute',
              bottom: '2rem',
              left: '50%',
              transform: 'translateX(-50%)',
              padding: '1rem 2rem',
              fontSize: '1.125rem',
            }}
            onClick={handleARView}
            disabled={!isHTTPS}
          >
            👋 View in AR
          </button>
        </div>
      )}
    </div>
  );
}
