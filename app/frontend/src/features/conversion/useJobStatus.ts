/**
 * TanStack Query hooks for VS-Conversion (ConversionJob).
 *
 * Polls job status every 5 seconds while status is pending/running.
 * Stops polling automatically when job reaches ready/failed.
 */
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/apiClient';
import type { ConversionJob, JobStatus } from '@/shared/api/types';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface JobStatusResponse {
  id: string;
  modelFileId: string;
  status: JobStatus;
  attempts: number;
  lastError: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  durationMs: number | null;
  glbUrl: string | null;
}

/* ------------------------------------------------------------------ */
/*  Query keys                                                         */
/* ------------------------------------------------------------------ */

export const jobKeys = {
  all: ['jobs'] as const,
  detail: (id: string) => [...jobKeys.all, id] as const,
};

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const POLL_INTERVAL_MS = 5000;
const TERMINAL_STATUSES: Set<JobStatus> = new Set(['ready', 'failed']);

/* ------------------------------------------------------------------ */
/*  Hooks                                                              */
/* ------------------------------------------------------------------ */

/**
 * Poll a conversion job's status.
 *
 * - Polls every 5s while status is 'pending' or 'running'
 * - Stops polling on 'ready' or 'failed'
 * - Returns the full job metadata including error message
 */
export function useJobStatus(jobId: string | null | undefined) {
  return useQuery({
    queryKey: jobKeys.detail(jobId ?? ''),
    queryFn: () =>
      apiClient.get<JobStatusResponse>(`/api/v1/jobs/${jobId}`),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || TERMINAL_STATUSES.has(data.status)) {
        return false; // Stop polling
      }
      return POLL_INTERVAL_MS;
    },
  });
}
