import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import ModelViewer from '../components/ModelViewer';
import { api, type PublicShareDto, type ProjectStatus } from '../api/client';
import { useArCapability } from '../auth/useArCapability';

type State =
  | { kind: 'loading' }
  | { kind: 'not-found' }
  | { kind: 'ready'; data: PublicShareDto };

export default function SharePage() {
  const { token = '' } = useParams<{ token: string }>();
  const [state, setState] = useState<State>({ kind: 'loading' });
  const arCapable = useArCapability();
  const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';

  useEffect(() => {
    let cancelled = false;
    setState({ kind: 'loading' });
    api
      .getPublicShare(token)
      .then((data) => {
        if (!cancelled) setState({ kind: 'ready', data });
      })
      .catch((err) => {
        if (cancelled) return;
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          setState({ kind: 'not-found' });
        } else {
          setState({ kind: 'not-found' });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (state.kind === 'loading') {
    return <div className="loading">Loading...</div>;
  }
  if (state.kind === 'not-found') {
    return (
      <div className="empty-state">
        <h1>We couldn&apos;t find that project</h1>
        <p>The link may be invalid or the project may not be published yet.</p>
      </div>
    );
  }

  const { data } = state;
  const status = data.status as ProjectStatus;
  const isPublished = status === 'Published';

  return (
    <div className="share-page">
      <header className="share-header">
        <h1>{data.name}</h1>
        {data.clientLabel && <p className="muted">for {data.clientLabel}</p>}
      </header>

      {!isPublished && (
        <div className="empty-state">
          <p>This project is not available for viewing yet (status: {status}).</p>
        </div>
      )}

      {isPublished && (
        <>
          <div className="viewer-wrap" data-testid="viewer">
            <ModelViewer
              glbUrl={data.glbUrl}
              thumbnailUrl={data.thumbnailUrl}
              alt={data.name}
            />
          </div>
          {arCapable && !isHttps && (
            <div className="banner" role="status">
              AR requires HTTPS. Use a secure URL to launch AR.
            </div>
          )}
        </>
      )}
    </div>
  );
}
