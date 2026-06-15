import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/shared/components/AppShell';
import { ErrorBoundary } from '@/shared/components/ErrorBoundary';
import { HomePage } from '@/pages/HomePage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ProjectDetailPage } from '@/pages/ProjectDetailPage';
import { ViewerPage } from '@/pages/ViewerPage';
import { SharePage } from '@/pages/SharePage';

export const AppRoutes = () => (
  <ErrorBoundary>
    <Routes>
      {/* Public share route — no shell. */}
      <Route path="/s/:token" element={<SharePage />} />

      {/* Viewer page — full screen, no shell. */}
      <Route path="/viewer/:fileId" element={<ViewerPage />} />

      {/* Routes wrapped in AppShell. */}
      <Route element={<AppShell />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </ErrorBoundary>
);
