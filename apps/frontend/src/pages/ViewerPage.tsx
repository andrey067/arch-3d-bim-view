/**
 * Sprint 4 — Viewer page.
 *
 * Displays a 3D model using <model-viewer> with full-screen layout.
 * Supports orbit, zoom, and camera reset via native controls.
 *
 * Route: /viewer/:fileId
 */
import { useParams, useNavigate } from 'react-router-dom';
import { useViewerMetadata, getApiUrl } from '@/features/viewer/useViewer';
import { ModelViewer } from '@/shared/components/ModelViewer';
import { Button, Card, Spinner } from '@/shared/components';

export const ViewerPage = () => {
  const { fileId } = useParams<{ fileId: string }>();
  const navigate = useNavigate();
  const { data: viewer, isLoading, error } = useViewerMetadata(fileId!);

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        gap: 'var(--space-4)',
      }}>
        <Spinner size={48} />
        <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
          Carregando metadados do modelo...
        </p>
      </div>
    );
  }

  if (error || !viewer) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        padding: 'var(--space-6)',
      }}>
        <Card style={{ maxWidth: 400, textAlign: 'center' }}>
          <p style={{ margin: 0, color: 'var(--color-danger)', fontWeight: 500 }}>
            Erro ao carregar modelo
          </p>
          <p style={{ margin: 'var(--space-2) 0 0', color: 'var(--color-text-muted)' }}>
            {error instanceof Error ? error.message : 'Modelo não encontrado.'}
          </p>
          <Button
            variant="primary"
            onClick={() => navigate(-1)}
            style={{ marginTop: 'var(--space-4)' }}
          >
            Voltar
          </Button>
        </Card>
      </div>
    );
  }

  // Conversion not ready
  if (viewer.status !== 'ready') {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        padding: 'var(--space-6)',
      }}>
        <Card style={{ maxWidth: 400, textAlign: 'center' }}>
          {viewer.status === 'pending' || viewer.status === 'running' ? (
            <>
              <Spinner size={32} />
              <p style={{ margin: 'var(--space-3) 0 0', color: 'var(--color-text-muted)' }}>
                Conversão em andamento...
              </p>
              <p style={{ margin: 'var(--space-1) 0 0', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                Status: {viewer.status === 'pending' ? 'Aguardando' : 'Processando'}
              </p>
            </>
          ) : (
            <>
              <p style={{ margin: 0, color: 'var(--color-danger)', fontWeight: 500 }}>
                Conversão falhou
              </p>
              {viewer.lastError && (
                <p style={{ margin: 'var(--space-2) 0 0', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                  {viewer.lastError}
                </p>
              )}
            </>
          )}
          <Button
            variant="ghost"
            onClick={() => navigate(-1)}
            style={{ marginTop: 'var(--space-4)' }}
          >
            Voltar
          </Button>
        </Card>
      </div>
    );
  }

  // Ready to view
  const glbUrl = viewer.glbUrl ? getApiUrl(viewer.glbUrl) : '';
  const thumbnailUrl = viewer.thumbnailUrl ? getApiUrl(viewer.thumbnailUrl) : undefined;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      background: 'var(--color-bg)',
    }}>
      {/* Header */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 'var(--space-3) var(--space-4)',
        background: 'var(--color-surface)',
        borderBottom: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-sm)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(-1)}
          >
            &larr; Voltar
          </Button>
          <div>
            <h1 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>
              {viewer.filename}
            </h1>
            <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
              {viewer.sourceFormat.toUpperCase()} • Visualizador 3D
            </p>
          </div>
        </div>
      </header>

      {/* Viewer */}
      <main style={{ flex: 1, overflow: 'hidden' }}>
        <ModelViewer
          src={glbUrl}
          poster={thumbnailUrl}
          alt={`3D model: ${viewer.filename}`}
          autoRotate={true}
          arEnabled={true}
          style={{ width: '100%', height: '100%' }}
        />
      </main>
    </div>
  );
};
