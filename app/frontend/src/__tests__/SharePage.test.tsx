import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import SharePage from '../pages/SharePage';
import { api } from '../api/client';
import { vi, describe, it, expect, afterEach } from 'vitest';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client');
  return {
    ...actual,
    api: {
      getPublicShare: vi.fn(),
    },
  };
});

const mockedApi = api as unknown as {
  getPublicShare: ReturnType<typeof vi.fn>;
};

function renderPage(token: string) {
  return render(
    <MemoryRouter initialEntries={[`/s/${token}`]}>
      <Routes>
        <Route path="/s/:token" element={<SharePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('SharePage', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders 3D viewer with correct glbUrl for published project', async () => {
    mockedApi.getPublicShare.mockResolvedValue({
      name: 'Living Room',
      status: 'Published',
      glbUrl: 'https://minio.example.com/model.glb',
      thumbnailUrl: 'https://minio.example.com/thumb.jpg',
    });

    renderPage('token-123');

    await waitFor(() => expect(screen.getByTestId('viewer')).toBeInTheDocument());
    const modelViewer = screen.getByTestId('model-viewer');
    expect(modelViewer).toHaveAttribute('src', 'https://minio.example.com/model.glb');
    expect(modelViewer).toHaveAttribute('poster', 'https://minio.example.com/thumb.jpg');
  });

  it('shows not-found for invalid token', async () => {
    mockedApi.getPublicShare.mockRejectedValue({ response: { status: 404 } });

    renderPage('invalid-token');

    await waitFor(() => expect(screen.getByText(/couldn't find that project/i)).toBeInTheDocument());
  });

  it('shows processing status for unpublished project', async () => {
    mockedApi.getPublicShare.mockResolvedValue({
      name: 'Kitchen',
      status: 'Processing',
      glbUrl: 'https://minio.example.com/model.glb',
      thumbnailUrl: 'https://minio.example.com/thumb.jpg',
    });

    renderPage('token-456');

    await waitFor(() => expect(screen.getByText(/not available for viewing yet/i)).toBeInTheDocument());
    expect(screen.queryByTestId('viewer')).not.toBeInTheDocument();
  });
});
