import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';
import ShareDialog from '../components/ShareDialog';
import { api, type ProjectSummaryDto, type PublishResultDto } from '../api/client';

export default function DashboardPage() {
  const [projects, setProjects] = useState<ProjectSummaryDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [share, setShare] = useState<{ publicUrl: string; qrCodeUrl: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.listProjects();
      setProjects(r.items);
    } catch (err) {
      setError('Failed to load projects.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onPublish = async (id: string) => {
    try {
      const r: PublishResultDto = await api.publishProject(id);
      setShare({ publicUrl: r.publicUrl, qrCodeUrl: r.qrCodeUrl });
    } catch {
      setError('Could not publish this project.');
    }
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Projects</h1>
        <div>
          <Link to="/upload" className="button primary">
            New project
          </Link>
        </div>
      </header>

      {loading && <div className="loading">Loading...</div>}
      {error && <div className="error">{error}</div>}

      {!loading && projects.length === 0 && (
        <div className="empty-state">
          <p>You don&apos;t have any projects yet.</p>
          <Link to="/upload" className="button primary">
            Upload your first .ifc
          </Link>
        </div>
      )}

      <ul className="project-list" data-testid="project-list">
        {projects.map((p) => (
          <li key={p.id} className="project-card card">
            <Link to={`/projects/${p.id}`}>
              {p.thumbnailUrl ? (
                <img src={p.thumbnailUrl} alt={p.name} className="thumb" />
              ) : (
                <div className="thumb placeholder">No preview yet</div>
              )}
            </Link>
            <div className="project-card-body">
              <h3>
                <Link to={`/projects/${p.id}`}>{p.name}</Link>
              </h3>
              {p.clientLabel && <p className="muted">{p.clientLabel}</p>}
              <p className="muted">{new Date(p.createdAt).toLocaleString()}</p>
              <StatusBadge status={p.status} />
              <div className="actions">
                <Link to={`/projects/${p.id}`} className="button">
                  Open
                </Link>
                {p.status === 'ReadyToPublish' && (
                  <button
                    className="button primary"
                    onClick={() => onPublish(p.id)}
                    data-testid={`publish-${p.id}`}
                  >
                    Publish
                  </button>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>

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
