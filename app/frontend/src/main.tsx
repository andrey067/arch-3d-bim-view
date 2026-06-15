import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
// Registers the <model-viewer> custom element globally (side-effect import).
import '@google/model-viewer';
import { Providers } from '@/app/providers';
import { App } from '@/app/App';
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
      <ToasterProvider>
        <App />
      </ToasterProvider>
    </Providers>
  </StrictMode>,
);
