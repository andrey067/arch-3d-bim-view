import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
// model-viewer is stubbed in setupTests.ts — do not import the real web component here.
vi.mock('@google/model-viewer', () => ({}));

import SharePage from '../pages/SharePage';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('SharePage', () => {
  it('renders model-viewer with glb and poster when share API succeeds', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          name: 'Sofa',
          status: 'Ready',
          glbUrl: 'https://test.local/files/abc/model.glb',
          usdzUrl: 'https://test.local/files/abc/model.usdz',
          thumbnailUrl: 'https://test.local/files/abc/thumbnail.png',
        }),
      }),
    );

    render(
      <MemoryRouter initialEntries={['/s/abcd']}>
        <Routes>
          <Route path="/s/:token" element={<SharePage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Sofa')).toBeInTheDocument();
    });

    const viewer = document.querySelector('model-viewer');
    expect(viewer).not.toBeNull();
    expect(viewer?.getAttribute('src')).toBe('https://test.local/files/abc/model.glb');
    expect(viewer?.getAttribute('poster')).toBe('https://test.local/files/abc/thumbnail.png');
  });

  it('shows rel="ar" fallback link on iOS user agent', async () => {
    Object.defineProperty(navigator, 'userAgent', {
      value:
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
      configurable: true,
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          name: 'Sofa',
          status: 'Ready',
          glbUrl: 'https://test.local/files/abc/model.glb',
          usdzUrl: 'https://test.local/files/abc/model.usdz',
          thumbnailUrl: 'https://test.local/files/abc/thumbnail.png',
        }),
      }),
    );

    render(
      <MemoryRouter initialEntries={['/s/abcd']}>
        <Routes>
          <Route path="/s/:token" element={<SharePage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Sofa')).toBeInTheDocument();
    });

    const arLink = document.querySelector('a[rel="ar"]');
    expect(arLink).not.toBeNull();
    expect(arLink?.getAttribute('href')).toBe('https://test.local/files/abc/model.usdz');
  });
});
