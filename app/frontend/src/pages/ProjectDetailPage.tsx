import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';
import ModelViewer from '../components/ModelViewer';
import ShareDialog from '../components/ShareDialog';
import { api, type ProjectDto, type ProjectStatus } from '../api/client';

export default function ProjectDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [share, setShare] = useState<{ publicUrl: string; qrCodeUrl: string } | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const p = await api.getProject(id);
      setProject(p);
      setError(null);
      return p;
    } catch {
      setError('Project not found.');
      return null;
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load().then((p) => {
      if (p && (p.status === 'UploadReceived' || p.status === 'Processing')) {
        pollRef.current = setInterval(async () => {
          const next = await load();
          if (next && next.status !== 'UploadReceived' && next.status !== 'Processing') {
            if (pollRef.current) clearInterval(pollRef.current);
          }
        }, 2000);
      }
    });
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [load]);

  const onPublish = async () => {
    try {
      const r = await api.publishProject(id);
      setShare({ publicUrl: r.publicUrl, qrCodeUrl: r.qrCodeUrl });
      await load();
    } catch {
      setError('Could not publish this project.');
    }
  };

  if (loading) return <div className="loading">Loading...</div>;
  if (error || !project) {
    return (
      <div className="empty-state">
        <h1>Project not found</h1>
        <button onClick={() => navigate('/')} className="button">
          Back to dashboard
        </button>
      </div>
    );
  }

  const status = project.status as ProjectStatus;
  const canPublish = status === 'ReadyToPublish';
  const glbPresignedUrl = project.thumbnailUrl; // placeholder: backend currently returns only thumb in detail

  return (
    <div className="project-detail">
      <header className="detail-header">
        <h1>{project.name}</h1>
        {project.clientLabel && <p className="muted">for {project.clientLabel}</p>}
        <StatusBadge status={status} />
      </header>

      {project.thumbnailUrl && (
        <div className="thumb-large">
          <img src={project.thumbnailUrl} alt={project.name} />
        </div>
      )}

      {project.errorMessage && (
        <div className="error" role="alert">
          {project.errorMessage}
        </div>
      )}

      <div className="actions">
        {canPublish && (
          <button onClick={onPublish} className="button primary" data-testid="publish">
            Publish
          </button>
        )}
      </div>

      {glbPresignedUrl && status === 'Published' && (
        <div className="viewer-wrap">
          <ModelViewer
            glbUrl={glbPresignedUrl}
            thumbnailUrl={project.thumbnailUrl || ''}
            alt={project.name}
          />
        </div>
      )}

      {share && (
        <ShareDialog
          open={true}
          publicUrl={share.publicUrl}
          qrCodeUrl={share.qrCodeUrl}
          onClose={() => setShare(null)}
        />
      )}
    </div>
  );
}
