import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
}

const baseStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '0.5rem',
  border: '1px solid transparent',
  borderRadius: 'var(--radius-md)',
  cursor: 'pointer',
  transition: 'background 0.15s ease, border-color 0.15s ease, color 0.15s ease',
  fontWeight: 500,
};

const variantStyle: Record<Variant, React.CSSProperties> = {
  primary: { background: 'var(--color-primary)', color: '#fff' },
  secondary: { background: 'var(--color-surface)', borderColor: 'var(--color-border)' },
  ghost: { background: 'transparent' },
};

const sizeStyle: Record<Size, React.CSSProperties> = {
  sm: { padding: '0.25rem 0.625rem', fontSize: 'var(--font-size-sm)' },
  md: { padding: '0.5rem 1rem', fontSize: 'var(--font-size-md)' },
  lg: { padding: '0.75rem 1.25rem', fontSize: 'var(--font-size-lg)' },
};

export const Button = ({ variant = 'primary', size = 'md', style, children, ...rest }: ButtonProps) => (
  <button
    type="button"
    {...rest}
    style={{ ...baseStyle, ...variantStyle[variant], ...sizeStyle[size], ...style }}
  >
    {children}
  </button>
);
