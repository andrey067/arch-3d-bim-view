/**
 * Sprint 5 — Share dialog component.
 *
 * Modal for creating share links, copying URLs, and managing existing links.
 * Shows list of existing shares with revoke capability.
 */
import { useState, useCallback } from 'react';
import {
  useCreateShare,
  useProjectShareLinks,
  useRevokeShare,
  type ShareListItem,
} from '@/features/sharing/useShare';
import { Button } from './Button';
import { Card } from './Card';
import { Spinner } from './Spinner';

interface ShareDialogProps {
  /** Whether the dialog is open. */
  isOpen: boolean;
  /** Close handler. */
  onClose: () => void;
  /** Project ID for listing shares. */
  projectId: string;
  /** Model file ID to share (must have a ready conversion). */
  modelFileId: string;
  /** Model filename for display. */
  filename: string;
}

export const ShareDialog = ({
  isOpen,
  onClose,
  projectId,
  modelFileId,
  filename,
}: ShareDialogProps) => {
  const createShare = useCreateShare(projectId);
  const { data: shares, isLoading: sharesLoading } = useProjectShareLinks(projectId);
  const revokeShare = useRevokeShare(projectId);

  const [createdUrl, setCreatedUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [revokeConfirmId, setRevokeConfirmId] = useState<string | null>(null);

  const handleCreate = useCallback(async () => {
    try {
      const result = await createShare.mutateAsync(modelFileId);
      setCreatedUrl(result.publicUrl);
      setCopied(false);
    } catch {
      // Error handled by mutation
    }
  }, [createShare, modelFileId]);

  const handleCopy = useCallback(async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select text
      const input = document.querySelector(`input[value="${url}"]`) as HTMLInputElement;
      if (input) {
        input.select();
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    }
  }, []);

  const handleRevoke = useCallback(
    async (shareId: string) => {
      try {
        await revokeShare.mutateAsync(shareId);
        setRevokeConfirmId(null);
      } catch {
        // Error handled by mutation
      }
    },
    [revokeShare],
  );

  // Filter shares for this specific model file
  const fileShares = shares?.filter((s) => s.modelFileId === modelFileId) ?? [];

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0, 0, 0, 0.5)',
        backdropFilter: 'blur(4px)',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Compartilhar modelo"
    >
      <Card
        style={{
          width: '100%',
          maxWidth: 480,
          maxHeight: '80vh',
          overflow: 'auto',
          margin: 'var(--space-4)',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 'var(--space-4)',
          }}
        >
          <h2 style={{ margin: 0, fontSize: 'var(--font-size-lg)' }}>
            Compartilhar
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Fechar">
            &times;
          </Button>
        </div>

        <p
          style={{
            margin: '0 0 var(--space-4)',
            color: 'var(--color-text-muted)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          {filename}
        </p>

        {/* Create new share */}
        {!createdUrl ? (
          <Button
            variant="primary"
            onClick={handleCreate}
            disabled={createShare.isPending}
            style={{ width: '100%', marginBottom: 'var(--space-4)' }}
          >
            {createShare.isPending ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <Spinner size={16} /> Gerando link...
              </span>
            ) : (
              'Gerar link publico'
            )}
          </Button>
        ) : (
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <p style={{ margin: '0 0 var(--space-2)', fontWeight: 500, fontSize: 'var(--font-size-sm)' }}>
              Link gerado:
            </p>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <input
                type="text"
                value={createdUrl}
                readOnly
                style={{
                  flex: 1,
                  padding: 'var(--space-2) var(--space-3)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--font-size-sm)',
                  background: 'var(--color-bg)',
                  color: 'var(--color-text)',
                }}
                onClick={(e) => (e.target as HTMLInputElement).select()}
              />
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleCopy(createdUrl)}
              >
                {copied ? 'Copiado!' : 'Copiar'}
              </Button>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCreatedUrl(null)}
              style={{ marginTop: 'var(--space-2)' }}
            >
              Gerar outro link
            </Button>
          </div>
        )}

        {/* Error */}
        {createShare.isError && (
          <div
            style={{
              padding: 'var(--space-3)',
              marginBottom: 'var(--space-4)',
              background: 'var(--color-danger)',
              color: '#fff',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            {createShare.error instanceof Error
              ? createShare.error.message
              : 'Erro ao gerar link.'}
          </div>
        )}

        {/* Existing shares */}
        <div>
          <h3 style={{ margin: '0 0 var(--space-3)', fontSize: 'var(--font-size-base)' }}>
            Links existentes
          </h3>

          {sharesLoading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-4)' }}>
              <Spinner />
            </div>
          )}

          {!sharesLoading && fileShares.length === 0 && (
            <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', textAlign: 'center' }}>
              Nenhum link criado ainda.
            </p>
          )}

          {fileShares.map((share) => (
            <ShareItem
              key={share.id}
              share={share}
              revokeConfirmId={revokeConfirmId}
              onRevokeConfirm={setRevokeConfirmId}
              onRevoke={handleRevoke}
              isRevoking={revokeShare.isPending}
            />
          ))}
        </div>
      </Card>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Share Item                                                         */
/* ------------------------------------------------------------------ */

interface ShareItemProps {
  share: ShareListItem;
  revokeConfirmId: string | null;
  onRevokeConfirm: (id: string | null) => void;
  onRevoke: (id: string) => void;
  isRevoking: boolean;
}

const ShareItem = ({
  share,
  revokeConfirmId,
  onRevokeConfirm,
  onRevoke,
  isRevoking,
}: ShareItemProps) => {
  const isRevoked = share.revokedAt !== null;
  const isConfirming = revokeConfirmId === share.id;

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 'var(--space-2) var(--space-3)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-sm)',
        marginBottom: 'var(--space-2)',
        opacity: isRevoked ? 0.6 : 1,
      }}
    >
      <div>
        <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', fontWeight: 500 }}>
          {isRevoked ? 'Revogado' : 'Ativo'}
        </p>
        <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
          {new Date(share.createdAt).toLocaleDateString('pt-BR')}
        </p>
      </div>

      {!isRevoked && (
        <div>
          {isConfirming ? (
            <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onRevokeConfirm(null)}
              >
                Cancelar
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onRevoke(share.id)}
                disabled={isRevoking}
                style={{ color: 'var(--color-danger)' }}
              >
                {isRevoking ? 'Revogando...' : 'Confirmar'}
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRevokeConfirm(share.id)}
              style={{ color: 'var(--color-danger)' }}
            >
              Revogar
            </Button>
          )}
        </div>
      )}
    </div>
  );
};
