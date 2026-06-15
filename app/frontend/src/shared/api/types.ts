/**
 * Domain types — mirrors backend schemas.
 */

export type UUID = string;
export type ISODateTime = string;

export type SourceFormat = 'ifc' | 'dae' | 'obj' | 'glb';
export type JobStatus = 'pending' | 'running' | 'ready' | 'failed';

export interface Project {
  id: UUID;
  ownerId: UUID;
  name: string;
  description: string | null;
  createdAt: ISODateTime;
  updatedAt: ISODateTime;
  archivedAt: ISODateTime | null;
}

export interface ModelFile {
  id: UUID;
  projectId: UUID;
  uploaderId: UUID;
  originalFilename: string;
  sourceFormat: SourceFormat;
  sizeBytes: number;
  originalStorageKey: string;
  uploadedAt: ISODateTime;
  contentHash: string;
}

export interface ConversionJob {
  id: UUID;
  modelFileId: UUID;
  status: JobStatus;
  attempts: number;
  lastError: string | null;
  startedAt: ISODateTime | null;
  finishedAt: ISODateTime | null;
  createdAt: ISODateTime;
  glbStorageKey: string | null;
  usdzStorageKey: string | null;
  qrStorageKey: string | null;
  durationMs: number | null;
}

export interface ShareLink {
  id: UUID;
  token: string;
  projectId: UUID;
  modelFileId: UUID;
  createdBy: UUID;
  createdAt: ISODateTime;
  revokedAt: ISODateTime | null;
}
