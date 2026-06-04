import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export interface Project {
  id: string;
  name: string;
  status: 'Uploaded' | 'Queued' | 'Processing' | 'Completed' | 'Failed';
  thumbnailUrl?: string;
  glbUrl?: string;
  description?: string;
  createdAt: string;
}

export interface ShareData {
  id: string;
  projectName: string;
  glbUrl: string;
  thumbnailUrl?: string;
  description?: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export const api = {
  getProjects: async (): Promise<Project[]> => {
    const response = await client.get<Project[]>('/projects');
    return response.data;
  },

  getProject: async (id: string): Promise<Project> => {
    const response = await client.get<Project>(`/projects/${id}`);
    return response.data;
  },

  uploadProject: async (
    file: File,
    name: string,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<Project> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);

    const response = await client.post<Project>('/projects/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress({
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage,
          });
        }
      },
    });

    return response.data;
  },

  getShareData: async (id: string): Promise<ShareData> => {
    const response = await client.get<ShareData>(`/share/${id}`);
    return response.data;
  },
};

export default client;
