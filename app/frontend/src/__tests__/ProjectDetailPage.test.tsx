import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProjectDetailPage from '../pages/ProjectDetailPage';
import { api } from '../api/client';
import { vi, describe, it, expect, afterEach } from 'vitest';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client');
  return {
    ...actual,
    api: {
      getProject: vi.fn(),
      publishProject: vi.fn(),
    },
  };
});

const mockedApi = api as unknown as {
  getProject: ReturnType<typeof vi.fn>;
  publishProject: ReturnType<typeof vi.fn>;
};

function renderPage(projectId: string) {
  return render(
    <MemoryRouter initialEntries={[`/projects/${projectId}`]}>
      <Routes>
        <Route path="/projects/:id" element={<ProjectDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProjectDetailPage', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders project thumbnail and status without 3D viewer', async () => {
    mockedApi.getProject.mockResolvedValue({
      id: 'proj-1',
      name: 'Living Room',
      status: 'ReadyToPublish',
      thumbnailUrl: 'https://minio.example.com/thumb.jpg',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    });

    renderPage('proj-1');

    await waitFor(() => expect(screen.getByText('Living Room')).toBeInTheDocument());
    expect(screen.getByAltText('Living Room')).toHaveAttribute('src', 'https://minio.example.com/thumb.jpg');
    expect(screen.queryByTestId('model-viewer')).not.toBeInTheDocument();
  });

  it('shows publish button when status is ReadyToPublish', async () => {
    mockedApi.getProject.mockResolvedValue({
      id: 'proj-1',
      name: 'Kitchen',
      status: 'ReadyToPublish',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    });

    renderPage('proj-1');

    await waitFor(() => expect(screen.getByTestId('publish')).toBeInTheDocument());
  });

  it('shows share link button when status is Published', async () => {
    mockedApi.getProject.mockResolvedValue({
      id: 'proj-1',
      name: 'Bathroom',
      status: 'Published',
      thumbnailUrl: 'https://minio.example.com/thumb.jpg',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
      publishedAt: '2024-01-02T00:00:00Z',
    });

    renderPage('proj-1');

    await waitFor(() => expect(screen.getByTestId('show-share')).toBeInTheDocument());
    expect(screen.queryByTestId('publish')).not.toBeInTheDocument();
  });

  it('opens share dialog when clicking show share link', async () => {
    mockedApi.getProject.mockResolvedValue({
      id: 'proj-1',
      name: 'Bathroom',
      status: 'Published',
      thumbnailUrl: 'https://minio.example.com/thumb.jpg',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
      publishedAt: '2024-01-02T00:00:00Z',
    });
    mockedApi.publishProject.mockResolvedValue({
      projectId: 'proj-1',
      publicToken: 'token-123',
      publicUrl: 'https://example.com/s/token-123',
      qrCodeUrl: 'https://example.com/qr.png',
    });

    renderPage('proj-1');

    await waitFor(() => expect(screen.getByTestId('show-share')).toBeInTheDocument());
    await userEvent.click(screen.getByTestId('show-share'));

    await waitFor(() => expect(screen.getByTestId('share-dialog')).toBeInTheDocument());
    expect(screen.getByTestId('qr-code')).toHaveAttribute('src', 'https://example.com/qr.png');
  });
});
