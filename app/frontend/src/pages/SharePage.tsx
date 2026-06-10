import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import '@google/model-viewer';

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';

interface ShareData {
  name: string;
  status: string;
  glbUrl: string | null;
  usdzUrl: string | null;
  thumbnailUrl: string | null;
}

type State =
  | { kind: 'loading' }
  | { kind: 'not-found' }
  | { kind: 'ready'; data: ShareData };

type ModelViewerElement = HTMLElement & {
  activateAR?: () => Promise<void>;
};

export default function SharePage() {
  const { token = '' } = useParams<{ token: string }>();
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [arStatus, setArStatus] = useState<string>('not-presenting');
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

  useEffect(() => {
    const el = modelRef.current;
    if (!el) return;
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ status: string }>).detail;
      setArStatus(detail.status);
    };
    el.addEventListener('ar-status-change', handler);
    return () => el.removeEventListener('ar-status-change', handler);
  }, [state.kind]);

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
  const arAvailable = Boolean(data.usdzUrl && data.glbUrl);

  return (
    <div className="container">
      <h1>{data.name}</h1>
      <p className="muted">
        Drag to orbit · scroll to zoom · on a phone, tap “View in your space” to launch AR
      </p>

      {data.status !== 'Ready' || !data.glbUrl ? (
        <div className="banner" role="status">
          Model is still processing. Refresh in a moment.
        </div>
      ) : (
        <div className="model-frame">
          {/* @ts-expect-error custom element */}
          <model-viewer
            ref={modelRef}
            src={data.glbUrl}
            ios-src={data.usdzUrl ?? undefined}
            poster={data.thumbnailUrl ?? undefined}
            alt={data.name}
            camera-controls=""
            touch-action="pan-y"
            shadow-intensity="1"
            exposure="1"
            auto-rotate=""
            ar={arAvailable ? '' : undefined}
            ar-modes="webxr scene-viewer quick-look"
            ar-scale="auto"
            camera-target="0 0.5m 0"
            min-camera-orbit="auto auto auto"
            max-camera-orbit="Infinity 180deg auto"
            style={{ width: '100%', height: '50vh', minHeight: '300px', backgroundColor: '#f0f0f0', display: 'block' }}
          />
        </div>
      )}

      {arAvailable && (
        <p className="muted" style={{ marginTop: 8 }}>
          AR status: {arStatus}
        </p>
      )}

      {!isHttps && (
        <div className="banner" role="status">
          AR requires HTTPS. Open this page over HTTPS to launch the AR session.
        </div>
      )}

      {arAvailable && arStatus === 'failed' && (
        <div className="banner" role="status">
          AR could not start. Ensure you are on HTTPS and the USDZ file loaded correctly.
        </div>
      )}

      {!arAvailable && data.status === 'Ready' && (
        <div className="banner" role="status">
          AR is unavailable for this model. The 3D viewer above still works.
        </div>
      )}
    </div>
  );
}
