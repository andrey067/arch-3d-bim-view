import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button, Card, Input } from '@/shared/components';
import { useAuth } from '@/features/auth/useAuth';

export const LoginPage = () => {
  const { login, status } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await login(email, password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      if (err instanceof Error) {
        const msg = err.message;
        if (msg.includes('401') || msg.includes('Invalid credentials')) {
          setError('Credenciais inválidas.');
        } else if (msg.includes('429')) {
          setError('Muitas tentativas. Tente novamente em instantes.');
        } else {
          setError(msg);
        }
      } else {
        setError('Erro ao entrar. Tente novamente.');
      }
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '2rem' }}>
      <Card style={{ width: '100%', maxWidth: 380 }}>
        <h1 style={{ marginTop: 0, fontSize: 'var(--font-size-xl)' }}>Entrar</h1>
        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Input
            label="E-mail"
            type="email"
            name="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <Input
            label="Senha"
            type="password"
            name="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          {error && (
            <p role="alert" style={{ color: 'var(--color-danger)', margin: 0 }}>
              {error}
            </p>
          )}
          <Button type="submit" disabled={status === 'loading'}>
            {status === 'loading' ? 'Entrando…' : 'Entrar'}
          </Button>
        </form>
        <p style={{ marginTop: '1rem', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
          Não tem conta?{' '}
          <Link to="/register" style={{ color: 'var(--color-primary)' }}>
            Cadastre-se
          </Link>
        </p>
      </Card>
    </div>
  );
};
