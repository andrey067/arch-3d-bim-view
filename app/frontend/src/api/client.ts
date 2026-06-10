import axios, { AxiosError, AxiosProgressEvent } from 'axios';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';

function newCorrelationId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  withCredentials: true,
});

client.interceptors.request.use((config) => {
  config.headers = config.headers ?? {};
  if (!config.headers['X-Correlation-Id']) {
    config.headers['X-Correlation-Id'] = newCorrelationId();
  }
  return config;
});

client.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => Promise.reject(err),
);

export type ProjectStatus =
  | 'UploadReceived'
  | 'Processing'
  | 'ReadyToPublish'
  | 'Published'
  | 'Failed';

export interface ProjectDto {
  id: string;
  name: string;
  description?: string | null;
  clientLabel?: string | null;
  status: ProjectStatus;
  thumbnailUrl?: string | null;
  ifcSizeBytes?: number | null;
  errorMessage?: string | null;
  createdAt: string;
  updatedAt: string;
  publishedAt?: string | null;
}

export interface ProjectSummaryDto {
  id: string;
  name: string;
  clientLabel?: string | null;
  status: ProjectStatus;
  thumbnailUrl?: string | null;
  createdAt: string;
}

export interface ProjectListResponse {
  items: ProjectSummaryDto[];
  nextCursor: string | null;
}

export interface PublishResultDto {
  projectId: string;
  publicToken: string;
  publicUrl: string;
  qrCodeUrl: string;
}

export interface PublicShareDto {
  name: string;
  clientLabel?: string | null;
  status: ProjectStatus;
  glbUrl: string;
  thumbnailUrl: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export const api = {
  async listProjects(): Promise<ProjectListResponse> {
    const r = await client.get<ProjectListResponse>('/api/projects');
    return r.data;
  },
  async getProject(id: string): Promise<ProjectDto> {
    const r = await client.get<ProjectDto>(`/api/projects/${id}`);
    return r.data;
  },
  async createProject(
    form: { name: string; description?: string; clientLabel?: string; file: File },
    onProgress?: (p: UploadProgress) => void,
  ): Promise<ProjectDto> {
    const fd = new FormData();
    fd.append('name', form.name);
    if (form.description) fd.append('description', form.description);
    if (form.clientLabel) fd.append('clientLabel', form.clientLabel);
    fd.append('file', form.file);
    const r = await client.post<ProjectDto>('/api/projects', fd, {
      onUploadProgress: (e: AxiosProgressEvent) => {
        if (onProgress && e.total) {
          onProgress({
            loaded: e.loaded,
            total: e.total,
            percentage: Math.round((e.loaded * 100) / e.total),
          });
        }
      },
    });
    return r.data;
  },
  async publishProject(id: string): Promise<PublishResultDto> {
    const r = await client.post<PublishResultDto>(`/api/projects/${id}/publish`);
    return r.data;
  },
  async getPublicShare(token: string): Promise<PublicShareDto> {
    const r = await client.get<PublicShareDto>(`/api/share/${token}`);
    return r.data;
  },
};

export default client;
