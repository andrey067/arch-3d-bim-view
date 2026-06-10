import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatusBadge from '../components/StatusBadge';
import type { ProjectStatus } from '../api/client';

describe('StatusBadge', () => {
  it('renders a human-readable label', () => {
    render(<StatusBadge status={'Published' as ProjectStatus} />);
    expect(screen.getByText('Published')).toBeInTheDocument();
  });

  it('renders all known statuses without crashing', () => {
    const expected: Array<[ProjectStatus, string]> = [
      ['UploadReceived', 'Upload received'],
      ['Processing', 'Processing'],
      ['ReadyToPublish', 'Ready to publish'],
      ['Published', 'Published'],
      ['Failed', 'Failed'],
    ];
    for (const [s, label] of expected) {
      const { unmount } = render(<StatusBadge status={s} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });
});
