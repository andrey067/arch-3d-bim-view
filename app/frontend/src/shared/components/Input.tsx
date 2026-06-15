import type { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string | null;
}

export const Input = ({ label, error, id, style, ...rest }: InputProps) => {
  const inputId = id ?? `input-${rest.name ?? Math.random().toString(36).slice(2)}`;
  return (
    <label htmlFor={inputId} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
      {label && <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>{label}</span>}
      <input
        id={inputId}
        {...rest}
        style={{
          padding: '0.5rem 0.75rem',
          borderRadius: 'var(--radius-md)',
          border: `1px solid ${error ? 'var(--color-danger)' : 'var(--color-border)'}`,
          background: 'var(--color-surface)',
          color: 'var(--color-text)',
          ...style,
        }}
      />
      {error && (
        <span role="alert" style={{ color: 'var(--color-danger)', fontSize: 'var(--font-size-sm)' }}>
          {error}
        </span>
      )}
    </label>
  );
};
