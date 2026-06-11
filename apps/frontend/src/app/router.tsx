import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/shared/components/AppShell';
import { ErrorBoundary } from '@/shared/components/ErrorBoundary';
import { HomePage } from '@/pages/HomePage';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ProjectDetailPage } from '@/pages/ProjectDetailPage';
import { ViewerPage } from '@/pages/ViewerPage';
import { SharePage } from '@/pages/SharePage';

export const AppRoutes = () => (
  <ErrorBoundary>
    <Routes>
      {/* Public share route — no shell. */}
      <Route path="/s/:token" element={<SharePage />} />

      {/* Auth pages — minimal layout, no shell. */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Viewer page — full screen, no shell. */}
      <Route path="/viewer/:fileId" element={<ViewerPage />} />

      {/* Private routes — wrapped in AppShell. */}
      <Route element={<AppShell />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </ErrorBoundary>
);
