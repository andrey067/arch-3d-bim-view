import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import SharePage from './pages/SharePage';

export default function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/s/:token" element={<SharePage />} />
        <Route path="*" element={<HomePage />} />
      </Routes>
    </div>
  );
}
