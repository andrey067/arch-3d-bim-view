import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Providers } from '@/app/providers';
import { App } from '@/app/App';
import { AuthProvider } from '@/features/auth/AuthProvider';
import { ToasterProvider } from '@/shared/components/Toaster';
import '@/shared/styles/tokens.css';
import '@/shared/styles/global.css';

const root = document.getElementById('root');
if (!root) {
  throw new Error('Root element #root not found in index.html');
}

createRoot(root).render(
  <StrictMode>
    <Providers>
      <AuthProvider>
        <ToasterProvider>
          <App />
        </ToasterProvider>
      </AuthProvider>
    </Providers>
  </StrictMode>,
);
