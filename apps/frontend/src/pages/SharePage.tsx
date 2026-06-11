/**
 * Sprint 5 — Public share page.
 *
 * Displays a 3D model using <model-viewer> for anonymous clients.
 * No authentication required. Token is the credential.
 *
 * Route: /s/:token
 */
import { useParams } from 'react-router-dom';
import { useShareManifest } from '@/features/sharing/useShareManifest';
import { ModelViewer } from '@/shared/components/ModelViewer';
import { Button, Card, Spinner } from '@/shared/components';

export const SharePage = () => {
  const { token } = useParams<{ token: string }>();
  const { data: manifest, isLoading, error } = useShareManifest(token!);

  // Update page title and meta tags dynamically
  if (manifest) {
    document.title = `${manifest.filename} — Visualizacao 3D`;

    // Inject OG meta tags for link previews
    const setMeta = (property: string, content: string) => {
      let meta = document.querySelector(`meta[property="${property}"]`);
      if (!meta) {
        meta = document.createElement('meta');
        meta.setAttribute('property', property);
        document.head.appendChild(meta);
      }
      meta.setAttribute('content', content);
    };

    setMeta('og:title', `${manifest.filename} — Visualizacao 3D`);
    setMeta('og:type', 'website');
    if (manifest.thumbnailUrl) {
      setMeta('og:image', manifest.thumbnailUrl);
    }
  }

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          gap: 'var(--space-4)',
          background: 'var(--color-bg)',
        }}
      >
        <Spinner size={48} />
        <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
          Carregando modelo...
        </p>
      </div>
    );
  }

  if (error || !manifest) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          padding: 'var(--space-6)',
          background: 'var(--color-bg)',
        }}
      >
        <Card style={{ maxWidth: 400, textAlign: 'center' }}>
          <p style={{ margin: 0, color: 'var(--color-danger)', fontWeight: 500, fontSize: 'var(--font-size-lg)' }}>
            Link invalido ou expirado
          </p>
          <p style={{ margin: 'var(--space-2) 0 0', color: 'var(--color-text-muted)' }}>
            Este link de compartilhamento nao e valido ou foi revogado.
          </p>
          <Button
            variant="primary"
            onClick={() => (window.location.href = '/')}
            style={{ marginTop: 'var(--space-4)' }}
          >
            Voltar ao inicio
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        background: 'var(--color-bg)',
      }}
    >
      {/* Header */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--space-3) var(--space-4)',
          background: 'var(--color-surface)',
          borderBottom: '1px solid var(--color-border)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>
            {manifest.filename}
          </h1>
          <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
            {manifest.sourceFormat.toUpperCase()} &middot; Visualizacao publica
          </p>
        </div>
        <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
          App 3D Viewer
        </p>
      </header>

      {/* Viewer */}
      <main style={{ flex: 1, overflow: 'hidden' }}>
        <ModelViewer
          src={manifest.glbUrl}
          poster={manifest.thumbnailUrl ?? undefined}
          alt={`3D model: ${manifest.filename}`}
          autoRotate={true}
          arEnabled={true}
          style={{ width: '100%', height: '100%' }}
        />
      </main>
    </div>
  );
};
