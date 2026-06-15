/**
 * Public share manifest hook.
 *
 * Fetches the manifest for a public share link (no auth required).
 * Used by the public SharePage to load model metadata.
 */
import { useQuery } from '@tanstack/react-query';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export interface ShareManifest {
  modelFileId: string;
  filename: string;
  sourceFormat: string;
  status: string;
  glbUrl: string;
  usdzUrl: string | null;
  qrUrl: string | null;
}

export function useShareManifest(token: string) {
  return useQuery({
    queryKey: ['share-manifest', token],
    queryFn: async (): Promise<ShareManifest> => {
      const response = await fetch(`${API_BASE}/s/${token}/manifest`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Link invalido ou expirado.');
        }
        throw new Error('Erro ao carregar modelo.');
      }
      const data = (await response.json()) as {
        model_file_id: string;
        filename: string;
        source_format: string;
        status: string;
        glb_url: string;
        usdz_url: string | null;
        qr_url: string | null;
      };
      return {
        modelFileId: data.model_file_id,
        filename: data.filename,
        sourceFormat: data.source_format,
        status: data.status,
        glbUrl: `${API_BASE}${data.glb_url}`,
        usdzUrl: data.usdz_url ? `${API_BASE}${data.usdz_url}` : null,
        qrUrl: data.qr_url ? `${API_BASE}${data.qr_url}` : null,
      };
    },
    retry: 1,
    staleTime: 60_000,
  });
}
