import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button, Card, Input } from '@/shared/components';
import { useAuth } from '@/features/auth/useAuth';

export const RegisterPage = () => {
  const { register, status } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    // Client-side validation
    if (password.length < 8) {
      setError('A senha deve ter pelo menos 8 caracteres.');
      return;
    }

    try {
      await register(email, password, displayName || undefined);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      if (err instanceof Error) {
        const msg = err.message;
        if (msg.includes('409') || msg.includes('already registered')) {
          setError('Este e-mail já está cadastrado.');
        } else if (msg.includes('422') || msg.includes('Password')) {
          setError('Senha inválida. Use pelo menos 8 caracteres.');
        } else {
          setError(msg);
        }
      } else {
        setError('Erro ao cadastrar. Tente novamente.');
      }
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '2rem' }}>
      <Card style={{ width: '100%', maxWidth: 380 }}>
        <h1 style={{ marginTop: 0, fontSize: 'var(--font-size-xl)' }}>Cadastro</h1>
        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Input
            label="Nome"
            type="text"
            name="display_name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            autoComplete="name"
          />
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
            autoComplete="new-password"
            minLength={8}
          />
          {error && (
            <p role="alert" style={{ color: 'var(--color-danger)', margin: 0 }}>
              {error}
            </p>
          )}
          <Button type="submit" disabled={status === 'loading'}>
            {status === 'loading' ? 'Cadastrando…' : 'Cadastrar'}
          </Button>
        </form>
        <p style={{ marginTop: '1rem', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
          Já tem conta?{' '}
          <Link to="/login" style={{ color: 'var(--color-primary)' }}>
            Entrar
          </Link>
        </p>
      </Card>
    </div>
  );
};
