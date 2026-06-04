import { Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import './App.css';

const ProjectsPage = lazy(() => import('./pages/ProjectsPage'));
const UploadPage = lazy(() => import('./pages/UploadPage'));
const ViewerPage = lazy(() => import('./pages/ViewerPage'));
const SharePage = lazy(() => import('./pages/SharePage'));
const ARViewerPage = lazy(() => import('./pages/ARViewerPage'));

function App() {
  return (
    <div className="app">
      <Suspense fallback={<div className="loading">Loading...</div>}>
        <Routes>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/view/:id" element={<ViewerPage />} />
          <Route path="/share/:id" element={<SharePage />} />
          <Route path="/share/:id/ar" element={<ARViewerPage />} />
        </Routes>
      </Suspense>
    </div>
  );
}

export default App;
