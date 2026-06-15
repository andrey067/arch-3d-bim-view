/**
 * Sprint 5 — Sharing data hooks.
 *
 * Provides hooks for creating, listing, and revoking share links.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/apiClient';

export interface ShareCreateResponse {
  shareId: string;
  token: string;
  publicUrl: string;
}

export interface ShareListItem {
  id: string;
  modelFileId: string;
  projectId: string;
  createdAt: string;
  revokedAt: string | null;
}

/**
 * Hook to create a share link for a model file.
 */
export function useCreateShare(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (modelFileId: string): Promise<ShareCreateResponse> => {
      const data = await apiClient.post<{
        share_id: string;
        token: string;
        public_url: string;
      }>(`/api/v1/files/${modelFileId}/share`);
      return {
        shareId: data.share_id,
        token: data.token,
        publicUrl: data.public_url,
      };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shares', projectId] });
    },
  });
}

/**
 * Hook to list all share links for the authenticated user.
 */
export function useShareLinks() {
  return useQuery({
    queryKey: ['shares'],
    queryFn: async (): Promise<ShareListItem[]> => {
      const data = await apiClient.get<{
        items: Array<{
          id: string;
          model_file_id: string;
          project_id: string;
          created_at: string;
          revoked_at: string | null;
        }>;
      }>('/api/v1/shares');
      return data.items.map((item) => ({
        id: item.id,
        modelFileId: item.model_file_id,
        projectId: item.project_id,
        createdAt: item.created_at,
        revokedAt: item.revoked_at,
      }));
    },
  });
}

/**
 * Hook to list share links for a specific project.
 */
export function useProjectShareLinks(projectId: string) {
  return useQuery({
    queryKey: ['shares', projectId],
    queryFn: async (): Promise<ShareListItem[]> => {
      const data = await apiClient.get<{
        items: Array<{
          id: string;
          model_file_id: string;
          project_id: string;
          created_at: string;
          revoked_at: string | null;
        }>;
      }>('/api/v1/shares');
      return data.items
        .filter((item) => item.project_id === projectId)
        .map((item) => ({
          id: item.id,
          modelFileId: item.model_file_id,
          projectId: item.project_id,
          createdAt: item.created_at,
          revokedAt: item.revoked_at,
        }));
    },
  });
}

/**
 * Hook to revoke a share link.
 */
export function useRevokeShare(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (shareId: string): Promise<void> => {
      await apiClient.delete(`/api/v1/shares/${shareId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shares', projectId] });
      queryClient.invalidateQueries({ queryKey: ['shares'] });
    },
  });
}
