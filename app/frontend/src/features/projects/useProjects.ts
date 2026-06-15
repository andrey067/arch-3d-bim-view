/**
 * TanStack Query hooks for VS-Projects.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/apiClient';
import type { Project } from '@/shared/api/types';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface ProjectListItem {
  id: string;
  name: string;
  description: string | null;
  createdAt: string;
  updatedAt: string;
  archivedAt: string | null;
  fileCount: number;
}

interface ProjectListResponse {
  items: ProjectListItem[];
  nextCursor: string | null;
}

interface CreateProjectInput {
  name: string;
  description?: string | undefined;
}

interface UpdateProjectInput {
  name?: string;
  description?: string;
}

/* ------------------------------------------------------------------ */
/*  Query keys                                                         */
/* ------------------------------------------------------------------ */

export const projectKeys = {
  all: ['projects'] as const,
  list: (archived = false) => [...projectKeys.all, 'list', archived] as const,
  detail: (id: string) => [...projectKeys.all, 'detail', id] as const,
};

/* ------------------------------------------------------------------ */
/*  Hooks                                                              */
/* ------------------------------------------------------------------ */

export function useProjects(archived = false) {
  return useQuery({
    queryKey: projectKeys.list(archived),
    queryFn: () =>
      apiClient.get<ProjectListResponse>(
        `/api/v1/projects?archived=${archived}`,
      ),
    select: (data) => data.items,
  });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => apiClient.get<Project>(`/api/v1/projects/${projectId}`),
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateProjectInput) =>
      apiClient.post<Project>('/api/v1/projects', input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateProjectInput) =>
      apiClient.patch<Project>(`/api/v1/projects/${projectId}`, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useArchiveProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<Project>(`/api/v1/projects/${projectId}/archive`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useUnarchiveProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.post<Project>(`/api/v1/projects/${projectId}/unarchive`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.delete<void>(`/api/v1/projects/${projectId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}
