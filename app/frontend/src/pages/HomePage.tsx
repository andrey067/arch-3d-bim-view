import { useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react';

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';

interface UploadResult {
  token: string;
  name: string;
  sourceFormat: string;
  status: string;
  shareUrl: string;
  qrSvg: string;
}

const MODEL_EXT = /\.(ifc|dae|obj)$/i;

function defaultName(filename: string): string {
  return filename.replace(MODEL_EXT, '');
}

export default function HomePage() {
  const [name, setName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [copied, setCopied] = useState(false);

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    if (f && !name) setName(defaultName(f.name));
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (!f) return;
    setFile(f);
    if (!name) setName(defaultName(f.name));
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!file) {
      setError('Pick an .ifc, .dae, or .obj file first.');
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      if (name.trim()) fd.append('name', name.trim());
      const r = await fetch(`${API_BASE}/upload`, { method: 'POST', body: fd });
      if (!r.ok) {
        const body = await r.text();
        throw new Error(`Upload failed (${r.status}): ${body}`);
      }
      const data = (await r.json()) as UploadResult;
      setResult(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const copyLink = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard not available */
    }
  };

  const reset = () => {
    setResult(null);
    setFile(null);
    setName('');
    setError(null);
  };

  return (
    <div className="container">
      <h1>Arch3DAR</h1>
      <p className="muted">
        Upload an IFC or SketchUp export (.dae / .obj), get a public link to view and place it in AR.
      </p>

      {!result && (
        <form onSubmit={onSubmit} className="card">
          <div className="sketchup-guide" style={{ marginBottom: 16, padding: 12, background: '#f5f5f0', borderRadius: 8 }}>
            <strong>Using SketchUp?</strong>
            <p style={{ margin: '8px 0 0' }}>
              Export your model first: <strong>File → Export → 3D Model → Collada (.dae)</strong>, then upload
              the <code>.dae</code> file here. Direct <code>.skp</code> upload is not supported.
            </p>
          </div>

          <label>Project name (optional)</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={200}
            placeholder="Living Room Sofa"
          />

          <label>3D model file (.ifc, .dae, .obj)</label>
          <div
            className={'dropzone' + (dragOver ? ' over' : '')}
            onClick={() => document.getElementById('file-input')?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
          >
            {file ? (
              <span>
                <strong>{file.name}</strong> · {Math.round(file.size / 1024)} KB
              </span>
            ) : (
              <span>Click or drop an .ifc, .dae, or .obj file here</span>
            )}
            <input
              id="file-input"
              type="file"
              accept=".ifc,.dae,.obj"
              onChange={onPick}
              style={{ display: 'none' }}
            />
          </div>

          {error && <div className="error">{error}</div>}

          <div className="row" style={{ marginTop: 12 }}>
            <button type="submit" className="button" disabled={busy || !file}>
              {busy ? 'Uploading & converting…' : 'Upload'}
            </button>
            {file && (
              <button type="button" className="button secondary" onClick={reset}>
                Clear
              </button>
            )}
          </div>
        </form>
      )}

      {result && (
        <div className="card">
          <div className="success">
            Ready: <strong>{result.name}</strong> ({result.sourceFormat.toUpperCase()})
          </div>
          <p className="muted">Status: {result.status}</p>

          <label>Share link</label>
          <div className="share-link">
            <input type="text" readOnly value={result.shareUrl} />
            <button type="button" onClick={copyLink}>
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>

          <label>QR code</label>
          <div className="qr" dangerouslySetInnerHTML={{ __html: result.qrSvg }} />

          <div className="row">
            <a className="button" href={result.shareUrl} target="_blank" rel="noreferrer">
              Open public page
            </a>
            <button type="button" className="button secondary" onClick={reset}>
              Upload another
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
