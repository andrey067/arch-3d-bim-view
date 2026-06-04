import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, ShareData } from '../api/client';

export default function SharePage() {
  const { id } = useParams<{ id: string }>();
  const [shareData, setShareData] = useState<ShareData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const loadShareData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getShareData(id);
        setShareData(data);

        // Set Open Graph meta tags
        if (data.projectName) {
          document.title = `${data.projectName} - Arch3DAR`;
        }

        const ogTitle = document.querySelector('meta[property="og:title"]') || document.createElement('meta');
        ogTitle.setAttribute('property', 'og:title');
        ogTitle.setAttribute('content', data.projectName || 'BIM Project');
        document.head.appendChild(ogTitle);

        if (data.description) {
          const ogDescription = document.querySelector('meta[property="og:description"]') || document.createElement('meta');
          ogDescription.setAttribute('property', 'og:description');
          ogDescription.setAttribute('content', data.description);
          document.head.appendChild(ogDescription);
        }

        if (data.thumbnailUrl) {
          const ogImage = document.querySelector('meta[property="og:image"]') || document.createElement('meta');
          ogImage.setAttribute('property', 'og:image');
          ogImage.setAttribute('content', data.thumbnailUrl);
          document.head.appendChild(ogImage);
        }
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
          <div>Loading project...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="not-found">
        <div className="not-found-code">404</div>
        <div className="not-found-title">Project Not Found</div>
        <div className="not-found-description">
          The project you're looking for doesn't exist or has been removed.
        </div>
        <Link to="/" className="btn btn-primary">
          Go to Homepage
        </Link>
      </div>
    );
  }

  return (
    <div className="share-container">
      <div className="share-header">
        <h1 className="share-title">{shareData?.projectName}</h1>
        {shareData?.description && (
          <p className="share-description">{shareData.description}</p>
        )}
        <Link to={`/share/${id}/ar`} className="btn btn-primary">
          👋 View in AR
        </Link>
      </div>

      {shareData?.glbUrl && (
        <div
          style={{
            background: 'white',
            borderRadius: '0.75rem',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              background: '#f8fafc',
              padding: '3rem',
              textAlign: 'center',
              minHeight: '400px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <p style={{ color: 'var(--text-secondary)' }}>
              3D Viewer - Use the View in AR button for augmented reality experience
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
