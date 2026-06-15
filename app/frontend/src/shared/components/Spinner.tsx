export const Spinner = ({ size = 24 }: { size?: number }) => (
  <span
    role="status"
    aria-label="Carregando"
    style={{
      display: 'inline-block',
      width: size,
      height: size,
      border: '2px solid var(--color-border)',
      borderTopColor: 'var(--color-primary)',
      borderRadius: '50%',
      animation: 'app3d-spin 0.8s linear infinite',
    }}
  />
);

// Inject the keyframes once on module load.
if (typeof document !== 'undefined' && !document.getElementById('app3d-spinner-style')) {
  const style = document.createElement('style');
  style.id = 'app3d-spinner-style';
  style.textContent = '@keyframes app3d-spin { to { transform: rotate(360deg); } }';
  document.head.appendChild(style);
}
