import { Link } from 'react-router-dom';
import { Card } from '@/shared/components';

export const HomePage = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
    <h1 style={{ fontSize: 'var(--font-size-xl)', margin: 0 }}>App 3D Viewer</h1>
    <Card>
      <p style={{ margin: 0 }}>
        Plataforma de visualização e compartilhamento de modelos 3D. Sprint 0 — fundação do projeto.
      </p>
    </Card>
    <p>
      <Link to="/dashboard">Ir para o dashboard →</Link>
    </p>
  </div>
);
