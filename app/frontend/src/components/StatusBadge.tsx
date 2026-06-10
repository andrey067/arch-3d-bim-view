import type { ProjectStatus } from '../api/client';

const LABELS: Record<ProjectStatus, string> = {
  UploadReceived: 'Upload received',
  Processing: 'Processing',
  ReadyToPublish: 'Ready to publish',
  Published: 'Published',
  Failed: 'Failed',
};

const TONE: Record<ProjectStatus, string> = {
  UploadReceived: 'badge-neutral',
  Processing: 'badge-progress',
  ReadyToPublish: 'badge-success',
  Published: 'badge-published',
  Failed: 'badge-error',
};

export interface StatusBadgeProps {
  status: ProjectStatus;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`badge ${TONE[status]}`}>{LABELS[status]}</span>;
}
