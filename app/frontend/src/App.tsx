import { Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import './App.css';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const UploadPage = lazy(() => import('./pages/UploadPage'));
const ProjectDetailPage = lazy(() => import('./pages/ProjectDetailPage'));
const SharePage = lazy(() => import('./pages/SharePage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

function App() {
  return (
    <div className="app">
      <Suspense fallback={<div className="loading">Loading...</div>}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/projects/:id" element={<ProjectDetailPage />} />
          <Route path="/s/:token" element={<SharePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </div>
  );
}

export default App;
