import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, Project } from '../api/client';

const statusClasses: Record<Project['status'], string> = {
  Uploaded: 'badge-uploaded',
  Queued: 'badge-queued',
  Processing: 'badge-processing',
  Completed: 'badge-completed',
  Failed: 'badge-failed',
};

function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}

function copyToClipboard(text: string, onSuccess: () => void) {
  navigator.clipboard.writeText(text).then(() => {
    onSuccess();
  }).catch(() => {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    onSuccess();
  });
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getProjects();
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = (id: string) => {
    const url = `${window.location.origin}/share/${id}`;
    copyToClipboard(url, () => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  if (loading) {
    return (
      <div className="page-container">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h1 className="page-title">Projects</h1>
          <Link to="/upload" className="btn btn-primary">
            + Upload New
          </Link>
        </div>
        <div className="grid grid-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="card">
              <div className="skeleton" style={{ height: '160px' }} />
              <div style={{ padding: '1rem' }}>
                <div className="skeleton" style={{ height: '24px', marginBottom: '0.5rem' }} />
                <div className="skeleton" style={{ height: '16px', width: '60%' }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="error-message">{error}</div>
        <button className="btn btn-secondary" onClick={loadProjects} style={{ marginTop: '1rem' }}>
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 className="page-title">Projects</h1>
        <Link to="/upload" className="btn btn-primary">
          + Upload New
        </Link>
      </div>

      {projects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📂</div>
          <div className="empty-state-title">No projects yet</div>
          <p>Upload your first IFC file to get started!</p>
          <Link to="/upload" className="btn btn-primary" style={{ marginTop: '1rem' }}>
            Upload IFC File
          </Link>
        </div>
      ) : (
        <div className="grid grid-2">
          {projects.map((project) => (
            <div key={project.id} className="card project-card">
              {project.thumbnailUrl ? (
                <img
                  src={project.thumbnailUrl}
                  alt={project.name}
                  className="project-thumbnail"
                />
              ) : (
                <div className="project-thumbnail-placeholder">🏗️</div>
              )}
              <div className="project-content">
                <h3 className="project-name">{project.name}</h3>
                <div className="project-meta">
                  <span className={`badge ${statusClasses[project.status]}`}>
                    {project.status}
                  </span>
                  <span style={{ marginLeft: '0.5rem' }}>
                    {formatDate(project.createdAt)}
                  </span>
                </div>
                <div className="project-actions">
                  <Link to={`/view/${project.id}`} className="btn btn-primary">
                    View
                  </Link>
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleCopyLink(project.id)}
                  >
                    {copiedId === project.id ? 'Copied!' : 'Copy Share Link'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
