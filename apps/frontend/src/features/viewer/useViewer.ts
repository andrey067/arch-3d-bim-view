/**
 * Sprint 4 — Viewer data hooks.
 *
 * Provides hooks for fetching viewer metadata and GLB/thumbnail URLs.
 */
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/apiClient';

export interface ViewerMetadata {
  modelFileId: string;
  projectId: string;
  filename: string;
  sourceFormat: string;
  status: string;
  glbUrl: string | null;
  thumbnailUrl: string | null;
  lastError: string | null;
}

/**
 * Hook to fetch viewer metadata for a model file.
 *
 * Polls while conversion is in progress (pending/running).
 * Stops polling when conversion is ready or failed.
 */
export function useViewerMetadata(fileId: string) {
  return useQuery({
    queryKey: ['viewer', fileId],
    queryFn: async (): Promise<ViewerMetadata> => {
      const data = await apiClient.get<{
        model_file_id: string;
        project_id: string;
        filename: string;
        source_format: string;
        status: string;
        glb_url: string | null;
        thumbnail_url: string | null;
        last_error: string | null;
      }>(`/api/v1/files/${fileId}/viewer`);

      return {
        modelFileId: data.model_file_id,
        projectId: data.project_id,
        filename: data.filename,
        sourceFormat: data.source_format,
        status: data.status,
        glbUrl: data.glb_url,
        thumbnailUrl: data.thumbnail_url,
        lastError: data.last_error,
      };
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'pending' || status === 'running') {
        return 2000; // Poll every 2s while converting
      }
      return false; // Stop polling
    },
    retry: 2,
  });
}

/**
 * Get the full URL for a relative API path.
 */
export function getApiUrl(path: string): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${baseUrl}${path}`;
}
