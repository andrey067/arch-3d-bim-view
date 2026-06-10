import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import DropZone from '../components/DropZone';
import { api, type UploadProgress } from '../api/client';

export default function UploadPage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [clientLabel, setClientLabel] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please choose a .ifc file.');
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const project = await api.createProject(
        { name, description, clientLabel, file },
        setProgress,
      );
      navigate(`/projects/${project.id}`);
    } catch (err: unknown) {
      const msg =
        typeof err === 'object' && err !== null && 'response' in err
          ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (err as any).response?.data?.detail ?? 'Upload failed.'
          : 'Upload failed.';
      setError(String(msg));
    } finally {
      setBusy(false);
      setProgress(null);
    }
  };

  return (
    <div className="upload-page">
      <h1>New project</h1>
      <form onSubmit={onSubmit} className="card">
        <label>
          Project name *
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={200}
            data-testid="name-input"
          />
        </label>
        <label>
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={2000}
            rows={3}
          />
        </label>
        <label>
          Client label
          <input
            value={clientLabel}
            onChange={(e) => setClientLabel(e.target.value)}
            maxLength={200}
          />
        </label>
        <DropZone onSelect={setFile} disabled={busy} />
        {file && (
          <p className="muted">
            Selected: {file.name} ({Math.round(file.size / 1024)} KB)
          </p>
        )}
        {progress && (
          <div className="progress" data-testid="upload-progress">
            <div className="progress-bar" style={{ width: `${progress.percentage}%` }} />
            <span className="muted">{progress.percentage}%</span>
          </div>
        )}
        {error && <div className="error">{error}</div>}
        <button
          type="submit"
          className="button primary"
          disabled={busy || !file || !name.trim()}
          data-testid="submit"
        >
          {busy ? 'Uploading...' : 'Upload'}
        </button>
      </form>
    </div>
  );
}
