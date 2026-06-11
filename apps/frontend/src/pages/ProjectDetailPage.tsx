/**
 * Sprint 2 — Project detail page with file list and upload widget.
 * Sprint 3 — Added conversion status display with polling.
 * Sprint 4 — Added thumbnail preview and viewer button.
 * Sprint 5 — Added share button and ShareDialog.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProject } from '@/features/projects/useProjects';
import {
  useModelFiles,
  useUploadFile,
  useDeleteModelFile,
} from '@/features/models/useModelFiles';
import type { ModelFile, JobStatus } from '@/shared/api/types';
import { Button, Card, Spinner } from '@/shared/components';
import { Thumbnail } from '@/shared/components/Thumbnail';
import { ShareDialog } from '@/shared/components/ShareDialog';

const ALLOWED_EXTENSIONS = ['.ifc', '.dae', '.obj', '.glb'];
const MAX_FILE_SIZE_MB = 100;

export const ProjectDetailPage = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { data: project, isLoading: projectLoading } = useProject(projectId!);
  const { data: files, isLoading: filesLoading } = useModelFiles(projectId!);
  const uploadFile = useUploadFile(projectId!);
  const deleteFile = useDeleteModelFile(projectId!);

  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Share dialog state
  const [shareFileId, setShareFileId] = useState<string | null>(null);
  const [shareFilename, setShareFilename] = useState<string>('');

  const validateFile = useCallback((file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Formato não suportado. Use: ${ALLOWED_EXTENSIONS.join(', ')}`;
    }
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      return `Arquivo excede o limite de ${MAX_FILE_SIZE_MB} MB.`;
    }
    if (file.size === 0) {
      return 'Arquivo está vazio.';
    }
    return null;
  }, []);

  const handleUpload = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setUploadError(validationError);
        return;
      }

      setUploadError(null);
      setUploadProgress(0);

      // Simulate progress (since we don't have XHR progress with fetch)
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev === null || prev >= 90) return prev;
          return prev + 10;
        });
      }, 200);

      try {
        await uploadFile.mutateAsync(file);
        setUploadProgress(100);
        setTimeout(() => setUploadProgress(null), 1000);
      } catch (err) {
        setUploadError(err instanceof Error ? err.message : 'Erro no upload.');
        setUploadProgress(null);
      } finally {
        clearInterval(progressInterval);
      }
    },
    [uploadFile, validateFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleUpload(file);
    },
    [handleUpload],
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleUpload(file);
      // Reset input so same file can be selected again
      e.target.value = '';
    },
    [handleUpload],
  );

  const handleDelete = useCallback(
    async (fileId: string, filename: string) => {
      if (window.confirm(`Tem certeza que deseja excluir "${filename}"?`)) {
        try {
          await deleteFile.mutateAsync(fileId);
        } catch {
          // Error handled by mutation
        }
      }
    },
    [deleteFile],
  );

  if (projectLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-6)' }}>
        <Spinner size={32} />
      </div>
    );
  }

  if (!project) {
    return (
      <Card>
        <p style={{ margin: 0, color: 'var(--color-danger)' }}>Projeto não encontrado.</p>
        <Button variant="ghost" onClick={() => navigate('/dashboard')} style={{ marginTop: 'var(--space-3)' }}>
          Voltar ao Dashboard
        </Button>
      </Card>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Button variant="ghost" size="sm" onClick={() => navigate('/dashboard')} style={{ marginBottom: 'var(--space-2)' }}>
            &larr; Voltar
          </Button>
          <h1 style={{ fontSize: 'var(--font-size-xl)', margin: 0 }}>{project.name}</h1>
          {project.description && (
            <p style={{ margin: 'var(--space-1) 0 0', color: 'var(--color-text-muted)' }}>
              {project.description}
            </p>
          )}
        </div>
      </div>

      {/* Upload area */}
      <Card
        style={{
          border: isDragOver ? '2px dashed var(--color-primary)' : '2px dashed var(--color-border)',
          background: isDragOver ? 'var(--color-primary)' + '10' : undefined,
          transition: 'all 0.2s ease',
          cursor: 'pointer',
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click();
        }}
        tabIndex={0}
        role="button"
        aria-label="Área de upload de arquivos"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_EXTENSIONS.join(',')}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        <div style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
          {uploadProgress !== null ? (
            <div>
              <Spinner size={32} />
              <p style={{ margin: 'var(--space-2) 0 0' }}>
                Enviando arquivo... {uploadProgress}%
              </p>
              <div
                style={{
                  marginTop: 'var(--space-2)',
                  height: 4,
                  background: 'var(--color-border)',
                  borderRadius: 2,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${uploadProgress}%`,
                    background: 'var(--color-primary)',
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>
            </div>
          ) : (
            <>
              <p style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--font-size-lg)' }}>
                Arraste um arquivo aqui ou clique para selecionar
              </p>
              <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                Formatos aceitos: {ALLOWED_EXTENSIONS.join(', ')} (máx. {MAX_FILE_SIZE_MB} MB)
              </p>
            </>
          )}
        </div>
      </Card>

      {/* Upload error */}
      {uploadError && (
        <Card style={{ background: 'var(--color-danger)', color: '#fff' }}>
          <p style={{ margin: 0 }}>{uploadError}</p>
        </Card>
      )}

      {/* Files list */}
      <div>
        <h2 style={{ fontSize: 'var(--font-size-lg)', margin: '0 0 var(--space-3)' }}>
          Arquivos do Projeto
        </h2>

        {filesLoading && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-4)' }}>
            <Spinner />
          </div>
        )}

        {!filesLoading && files && files.length === 0 && (
          <Card>
            <p style={{ margin: 0, color: 'var(--color-text-muted)', textAlign: 'center' }}>
              Nenhum arquivo enviado ainda.
            </p>
          </Card>
        )}

        {!filesLoading && files && files.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {files.map((file) => (
              <FileCard
                key={file.id}
                file={file}
                onDelete={() => handleDelete(file.id, file.originalFilename)}
                onShare={(fileId, filename) => {
                  setShareFileId(fileId);
                  setShareFilename(filename);
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Share Dialog */}
      {shareFileId && projectId && (
        <ShareDialog
          isOpen={shareFileId !== null}
          onClose={() => setShareFileId(null)}
          projectId={projectId}
          modelFileId={shareFileId}
          filename={shareFilename}
        />
      )}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  File Card                                                          */
/* ------------------------------------------------------------------ */

interface FileCardProps {
  file: ModelFile;
  onDelete: () => void;
  onShare: (fileId: string, filename: string) => void;
}

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatBadge = (format: string): React.CSSProperties => ({
  display: 'inline-block',
  padding: '0.125rem 0.5rem',
  borderRadius: 'var(--radius-sm)',
  background: 'var(--color-primary)',
  color: '#fff',
  fontSize: 'var(--font-size-sm)',
  fontWeight: 600,
  textTransform: 'uppercase',
});

/* ------------------------------------------------------------------ */
/*  Conversion Status Badge                                            */
/* ------------------------------------------------------------------ */

const STATUS_COLORS: Record<JobStatus, string> = {
  pending: 'var(--color-text-muted)',
  running: 'var(--color-primary)',
  ready: 'var(--color-success, #22c55e)',
  failed: 'var(--color-danger)',
};

const STATUS_LABELS: Record<JobStatus, string> = {
  pending: 'Aguardando',
  running: 'Processando',
  ready: 'Convertido',
  failed: 'Falhou',
};

const ConversionStatusBadge = ({ fileId }: { fileId: string }) => {
  const [status, setStatus] = useState<JobStatus>('pending');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const POLL_INTERVAL = 5000;
    let timer: ReturnType<typeof setInterval> | null = null;
    let aborted = false;

    const fetchStatus = async () => {
      try {
        const token = localStorage.getItem('app3d.access_token');
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

        // We need to get the job for this file. Use the files endpoint.
        // For now, we'll query via the job endpoint if we have a jobId.
        // The upload response returns conversionJobId, so we can track it.
        // Since we don't have the jobId in the ModelFile type, we'll
        // use a simple approach: poll the file's status indirectly.

        // Actually, we can check the file detail endpoint which should
        // include job status info. For MVP, let's use a direct approach.
        const response = await fetch(
          `${baseUrl}/api/v1/files/${fileId}/status`,
          {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          },
        );

        if (aborted) return;

        if (response.ok) {
          const data = (await response.json()) as { status: JobStatus; lastError?: string };
          setStatus(data.status);
          setError(data.lastError ?? null);

          if (data.status === 'ready' || data.status === 'failed') {
            if (timer) clearInterval(timer);
          }
        }
      } catch {
        // Silently ignore polling errors
      }
    };

    fetchStatus();
    timer = setInterval(fetchStatus, POLL_INTERVAL);

    return () => {
      aborted = true;
      if (timer) clearInterval(timer);
    };
  }, [fileId]);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
      {status === 'running' && <Spinner size={14} />}
      <span
        style={{
          display: 'inline-block',
          padding: '0.125rem 0.5rem',
          borderRadius: 'var(--radius-sm)',
          background: STATUS_COLORS[status],
          color: status === 'pending' ? 'var(--color-text)' : '#fff',
          fontSize: 'var(--font-size-sm)',
          fontWeight: 600,
        }}
      >
        {STATUS_LABELS[status]}
      </span>
      {status === 'failed' && error && (
        <span
          style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-danger)' }}
          title={error}
        >
          (erro)
        </span>
      )}
    </div>
  );
};

const FileCard = ({ file, onDelete, onShare }: FileCardProps) => {
  const navigate = useNavigate();
  const [status, setStatus] = useState<JobStatus>('pending');

  // Poll conversion status
  useEffect(() => {
    const POLL_INTERVAL = 5000;
    let timer: ReturnType<typeof setInterval> | null = null;
    let aborted = false;

    const fetchStatus = async () => {
      try {
        const token = localStorage.getItem('app3d.access_token');
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(
          `${baseUrl}/api/v1/files/${file.id}/status`,
          { headers: token ? { Authorization: `Bearer ${token}` } : {} },
        );

        if (aborted) return;

        if (response.ok) {
          const data = (await response.json()) as { status: JobStatus; lastError?: string };
          setStatus(data.status);

          if (data.status === 'ready' || data.status === 'failed') {
            if (timer) clearInterval(timer);
          }
        }
      } catch {
        // Silently ignore polling errors
      }
    };

    fetchStatus();
    timer = setInterval(fetchStatus, POLL_INTERVAL);

    return () => {
      aborted = true;
      if (timer) clearInterval(timer);
    };
  }, [file.id]);

  return (
    <Card>
      <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
        {/* Thumbnail */}
        {status === 'ready' && (
          <div style={{ flexShrink: 0, width: 120, height: 90 }}>
            <Thumbnail
              modelFileId={file.id}
              alt={`Thumbnail of ${file.originalFilename}`}
              style={{ width: '100%', height: '100%', borderRadius: 'var(--radius-sm)' }}
            />
          </div>
        )}

        {/* File info */}
        <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <span style={formatBadge(file.sourceFormat)}>{file.sourceFormat}</span>
            <div>
              <p style={{ margin: 0, fontWeight: 500 }}>{file.originalFilename}</p>
              <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                {formatSize(file.sizeBytes)} &middot; Enviado em {new Date(file.uploadedAt).toLocaleDateString('pt-BR')}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <ConversionStatusBadge fileId={file.id} />

            {/* View button - only shown when conversion is ready */}
            {status === 'ready' && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate(`/viewer/${file.id}`)}
              >
                Visualizar
              </Button>
            )}

            {/* Share button - only shown when conversion is ready */}
            {status === 'ready' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onShare(file.id, file.originalFilename)}
              >
                Compartilhar
              </Button>
            )}

            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              style={{ color: 'var(--color-danger)' }}
            >
              Excluir
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
};
