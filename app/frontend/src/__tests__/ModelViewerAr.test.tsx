import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
vi.mock('@google/model-viewer', () => ({}));

import SharePage from '../pages/SharePage';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('SharePage AR attributes', () => {
  it('sets ios-src and quick-look-first ar-modes when usdzUrl is provided', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          name: 'Chair',
          status: 'Ready',
          glbUrl: 'https://test.local/files/id/model.glb',
          usdzUrl: 'https://test.local/files/id/model.usdz',
          thumbnailUrl: 'https://test.local/files/id/thumbnail.png',
        }),
      }),
    );

    render(
      <MemoryRouter initialEntries={['/s/token']}>
        <Routes>
          <Route path="/s/:token" element={<SharePage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Chair')).toBeInTheDocument();
    });

    const viewer = document.querySelector('model-viewer');
    expect(viewer?.getAttribute('ios-src')).toBe('https://test.local/files/id/model.usdz');
    expect(viewer?.getAttribute('ar-modes')).toBe('quick-look scene-viewer webxr');
    expect(viewer?.hasAttribute('ar')).toBe(true);
  });
});
