/**
 * Sprint 4 — ModelViewer wrapper component.
 *
 * Wraps Google's <model-viewer> web component with TypeScript types,
 * loading states, and error handling. Uses native orbit/zoom controls.
 *
 * @see https://modelviewer.dev/
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { Spinner } from './Spinner';

// Extend JSX IntrinsicElements for model-viewer
declare global {
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          src?: string;
          poster?: string | undefined;
          alt?: string;
          'camera-controls'?: boolean;
          'auto-rotate'?: boolean;
          'auto-rotate-delay'?: string;
          'rotation-per-second'?: string;
          'interaction-prompt'?: string;
          'touch-action'?: string;
          'disable-zoom'?: boolean;
          'min-camera-orbit'?: string;
          'max-camera-orbit'?: string;
          'min-field-of-view'?: string;
          'max-field-of-view'?: string;
          'camera-orbit'?: string;
          'field-of-view'?: string;
          'auto-play'?: boolean;
          'animation-name'?: string;
          'shadow-intensity'?: string;
          'shadow-softness'?: string;
          'environment-image'?: string;
          exposure?: string;
          // AR attributes
          ar?: boolean;
          'ar-modes'?: string;
          'ar-scale'?: string;
          'ar-placement'?: string;
          'ios-src'?: string;
          style?: React.CSSProperties;
        },
        HTMLElement
      >;
    }
  }
}

// AR Icon component
const ARIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 2L2 7l10 5 10-5-10-5z" />
    <path d="M2 17l10 5 10-5" />
    <path d="M2 12l10 5 10-5" />
  </svg>
);

interface ModelViewerProps {
  /** URL to the GLB file. */
  src: string;
  /** URL to USDZ file for iOS Quick Look AR. */
  iosSrc?: string | undefined;
  /** URL to thumbnail/poster image. */
  poster?: string | undefined;
  /** Alt text for accessibility. */
  alt?: string;
  /** Enable auto-rotation. Default: true. */
  autoRotate?: boolean;
  /** Enable AR functionality. Default: false. */
  arEnabled?: boolean;
  /** Callback when model loads successfully. */
  onLoad?: () => void;
  /** Callback when model fails to load. */
  onError?: (error: string) => void;
  /** Optional CSS class name. */
  className?: string;
  /** Optional inline styles. */
  style?: React.CSSProperties;
}

export const ModelViewer = ({
  src,
  iosSrc,
  poster,
  alt = '3D Model',
  autoRotate = true,
  arEnabled = false,
  onLoad,
  onError,
  className,
  style,
}: ModelViewerProps) => {
  const viewerRef = useRef<HTMLElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [arSupported, setArSupported] = useState<boolean | null>(null);
  const [arLoading, setArLoading] = useState(false);

  // Detect if running on HTTP (not HTTPS) - for dev banner
  const isHTTP = typeof window !== 'undefined' && window.location.protocol === 'http:';

  // Detect AR support (WebXR for Android, iOS Quick Look detection)
  useEffect(() => {
    if (!arEnabled) {
      setArSupported(false);
      return;
    }

    // Check if we're in a secure context (HTTPS)
    const isSecureContext = window.isSecureContext;
    if (!isSecureContext) {
      setArSupported(false);
      return;
    }

    // Detect iOS (Quick Look requires USDZ, but model-viewer handles fallback)
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

    // For iOS, assume AR is supported (Quick Look)
    if (isIOS) {
      setArSupported(true);
      return;
    }

    // For Android/other, check WebXR support
    const checkWebXR = async () => {
      try {
        if ('xr' in navigator) {
          const xr = (navigator as unknown as { xr: { isSessionSupported: (mode: string) => Promise<boolean> } }).xr;
          const supported = await xr.isSessionSupported('immersive-ar');
          setArSupported(supported);
        } else {
          setArSupported(false);
        }
      } catch {
        setArSupported(false);
      }
    };

    checkWebXR();
  }, [arEnabled]);

  const handleLoad = useCallback(() => {
    setIsLoading(false);
    setHasError(false);
    onLoad?.();
  }, [onLoad]);

  const handleError = useCallback(
    (event: Event) => {
      setIsLoading(false);
      setHasError(true);
      const msg = 'Failed to load 3D model.';
      setErrorMessage(msg);
      onError?.(msg);
    },
    [onError],
  );

  const handleResetCamera = useCallback(() => {
    if (viewerRef.current) {
      // Reset camera to default orbit
      viewerRef.current.setAttribute('camera-orbit', '0deg 75deg 105%');
      viewerRef.current.setAttribute('field-of-view', '30deg');
    }
  }, []);

  const handleActivateAR = useCallback(() => {
    if (viewerRef.current) {
      setArLoading(true);
      try {
        // model-viewer handles AR activation internally
        const viewer = viewerRef.current as HTMLElement & { activateAR?: () => Promise<void> };
        if (viewer.activateAR) {
          viewer.activateAR();
        }
      } catch (err) {
        onError?.('Failed to activate AR');
      } finally {
        setArLoading(false);
      }
    }
  }, [onError]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    viewer.addEventListener('load', handleLoad);
    viewer.addEventListener('error', handleError);

    return () => {
      viewer.removeEventListener('load', handleLoad);
      viewer.removeEventListener('error', handleError);
    };
  }, [handleLoad, handleError]);

  const containerStyle: React.CSSProperties = {
    position: 'relative',
    width: '100%',
    height: '100%',
    minHeight: 400,
    ...style,
  };

  const viewerStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    backgroundColor: '#f0f1f6',
  };

  const controlsStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: 'var(--space-4)',
    right: 'var(--space-4)',
    display: 'flex',
    gap: 'var(--space-2)',
    zIndex: 10,
  };

  const buttonStyle: React.CSSProperties = {
    padding: 'var(--space-2) var(--space-3)',
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    fontSize: 'var(--font-size-sm)',
    color: 'var(--color-text)',
    boxShadow: 'var(--shadow-sm)',
    transition: 'background 0.2s ease',
  };

  const overlayStyle: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(240, 241, 246, 0.9)',
    zIndex: 20,
  };

  return (
    <div className={className} style={containerStyle}>
      {/* HTTPS warning banner for AR in development */}
      {arEnabled && isHTTP && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          padding: 'var(--space-2) var(--space-4)',
          background: 'var(--color-warning-bg, #fff3cd)',
          borderBottom: '1px solid var(--color-warning-border, #ffc107)',
          color: 'var(--color-warning-text, #856404)',
          fontSize: 'var(--font-size-sm)',
          textAlign: 'center',
          zIndex: 30,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 'var(--space-2)',
        }}>
          <span style={{ fontWeight: 500 }}>AR requer HTTPS</span>
          <span>
            Use <code style={{ background: 'rgba(0,0,0,0.1)', padding: '2px 6px', borderRadius: '4px' }}>https://localhost</code> ou um tunnel (ngrok, Cloudflare Tunnel)
          </span>
        </div>
      )}

      {/* Loading overlay */}
      {isLoading && !hasError && (
        <div style={overlayStyle}>
          <Spinner size={32} />
          <p style={{ margin: 'var(--space-2) 0 0', color: 'var(--color-text-muted)' }}>
            Carregando modelo 3D...
          </p>
        </div>
      )}

      {/* Error overlay */}
      {hasError && (
        <div style={overlayStyle}>
          <p style={{ margin: 0, color: 'var(--color-danger)', fontWeight: 500 }}>
            Erro ao carregar modelo
          </p>
          {errorMessage && (
            <p style={{ margin: 'var(--space-1) 0 0', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
              {errorMessage}
            </p>
          )}
        </div>
      )}

      {/* model-viewer element */}
      <model-viewer
        ref={viewerRef}
        src={src}
        {...(poster ? { poster } : {})}
        alt={alt}
        camera-controls
        {...(autoRotate ? { 'auto-rotate': true } : {})}
        auto-rotate-delay="1000"
        rotation-per-second="30deg"
        interaction-prompt="auto"
        touch-action="pan-y"
        shadow-intensity="1"
        shadow-softness="0.5"
        {...(arEnabled && arSupported ? {
          ar: true,
          'ar-modes': 'webxr scene-viewer quick-look',
          'ar-scale': 'auto',
          'ar-placement': 'floor',
          ...(iosSrc ? { 'ios-src': iosSrc } : {}),
        } : {})}
        style={viewerStyle}
      />

      {/* Camera controls */}
      {!isLoading && !hasError && (
        <div style={controlsStyle}>
          {/* AR button - only show on supported devices */}
          {arEnabled && arSupported && (
            <button
              type="button"
              onClick={handleActivateAR}
              disabled={arLoading}
              style={{
                ...buttonStyle,
                background: 'var(--color-primary)',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-primary-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--color-primary)';
              }}
              title="Visualizar em Realidade Aumentada"
            >
              {arLoading ? (
                <>
                  <Spinner size={16} />
                  Carregando AR...
                </>
              ) : (
                <>
                  <ARIcon />
                  Visualizar em AR
                </>
              )}
            </button>
          )}

          {/* Desktop message when AR not supported */}
          {arEnabled && arSupported === false && (
            <span style={{
              ...buttonStyle,
              cursor: 'default',
              opacity: 0.7,
              fontSize: 'var(--font-size-xs)',
            }}>
              AR indisponivel neste dispositivo
            </span>
          )}

          <button
            type="button"
            onClick={handleResetCamera}
            style={buttonStyle}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--color-surface-hover)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--color-surface)';
            }}
            title="Reset camera position"
          >
            ↺ Reset
          </button>
        </div>
      )}
    </div>
  );
};
