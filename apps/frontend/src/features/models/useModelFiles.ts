/**
 * TanStack Query hooks for VS-Upload (ModelFile).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/apiClient';
import type { ModelFile } from '@/shared/api/types';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ModelFileListResponse {
  items: ModelFile[];
  nextCursor: string | null;
}

interface UploadResponse {
  modelFileId: string;
  conversionJobId: string;
  status: string;
}

/* ------------------------------------------------------------------ */
/*  Query keys                                                         */
/* ------------------------------------------------------------------ */

export const modelFileKeys = {
  all: ['modelFiles'] as const,
  list: (projectId: string) => [...modelFileKeys.all, 'list', projectId] as const,
  detail: (id: string) => [...modelFileKeys.all, 'detail', id] as const,
};

/* ------------------------------------------------------------------ */
/*  Hooks                                                              */
/* ------------------------------------------------------------------ */

export function useModelFiles(projectId: string) {
  return useQuery({
    queryKey: modelFileKeys.list(projectId),
    queryFn: () =>
      apiClient.get<ModelFileListResponse>(
        `/api/v1/projects/${projectId}/files`,
      ),
    select: (data) => data.items,
    enabled: !!projectId,
  });
}

export function useUploadFile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File): Promise<UploadResponse> => {
      const formData = new FormData();
      formData.append('file', file);

      // Use fetch directly for FormData (apiClient doesn't handle multipart well)
      const token = localStorage.getItem('app3d.access_token');
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(
        `${baseUrl}/api/v1/projects/${projectId}/files`,
        {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        },
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message =
          (errorData as { error?: { message?: string } })?.error?.message ||
          `Upload failed with status ${response.status}`;
        throw new Error(message);
      }

      return (await response.json()) as UploadResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: modelFileKeys.list(projectId),
      });
    },
  });
}

export function useDeleteModelFile(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fileId: string) =>
      apiClient.delete<void>(`/api/v1/files/${fileId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: modelFileKeys.list(projectId),
      });
    },
  });
}
