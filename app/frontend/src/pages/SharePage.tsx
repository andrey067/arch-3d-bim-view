import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import '@google/model-viewer';

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';

interface ShareData {
  name: string;
  glbUrl: string;
  usdzUrl: string | null;
  thumbnailUrl: string;
}

type State =
  | { kind: 'loading' }
  | { kind: 'not-found' }
  | { kind: 'ready'; data: ShareData };

// The <model-viewer> custom element is registered by the import above.
// We treat it as a generic HTMLElement to keep TypeScript happy.
type ModelViewerElement = HTMLElement & {
  activateAR?: () => Promise<void>;
};

export default function SharePage() {
  const { token = '' } = useParams<{ token: string }>();
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [arStatus, setArStatus] = useState<string>('idle');
  const modelRef = useRef<ModelViewerElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState({ kind: 'loading' });
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/share/${encodeURIComponent(token)}`);
        if (cancelled) return;
        if (r.status === 404 || !r.ok) {
          setState({ kind: 'not-found' });
          return;
        }
        const data = (await r.json()) as ShareData;
        if (!cancelled) setState({ kind: 'ready', data });
      } catch {
        if (!cancelled) setState({ kind: 'not-found' });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (state.kind === 'loading') {
    return (
      <div className="container">
        <p className="muted">Loading…</p>
      </div>
    );
  }
  if (state.kind === 'not-found') {
    return (
      <div className="container">
        <h1>Not found</h1>
        <p className="muted">This link is invalid or the model is not available.</p>
      </div>
    );
  }

  const { data } = state;
  const isHttps = window.location.protocol === 'https:';

  return (
    <div className="container">
      <h1>{data.name}</h1>
      <p className="muted">
        Drag to orbit · scroll to zoom · on a phone, tap “View in your space” to launch AR
      </p>

      <div className="model-frame">
        {/* @ts-expect-error custom element */}
        <model-viewer
          ref={modelRef}
          src={data.glbUrl}
          ios-src={data.usdzUrl ?? ''}
          poster={data.thumbnailUrl}
          alt={data.name}
          camera-controls=""
          touch-action="pan-y"
          shadow-intensity="1"
          exposure="1"
          ar=""
          ar-modes="quick-look scene-viewer webxr"
          ar-status="not-presenting"
          style={{ width: '100%', height: '100%', backgroundColor: '#f0f0f0', display: 'block' }}
          onArStatus={(e: Event) => {
            const detail = (e as CustomEvent<{ status: string }>).detail;
            setArStatus(detail.status);
          }}
        />
      </div>

      <p className="muted" style={{ marginTop: 8 }}>
        AR status: {arStatus}
      </p>

      {!isHttps && (
        <div className="banner" role="status">
          AR requires HTTPS. Open this page over HTTPS to launch the AR session.
        </div>
      )}

      {arStatus === 'unsupported' && (
        <div className="banner" role="status">
          This device/browser does not support AR. The 3D viewer above still works.
        </div>
      )}
    </div>
  );
}
