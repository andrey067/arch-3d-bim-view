/**
 * Sprint 4 — Thumbnail component with fallback and skeleton.
 *
 * Displays a model thumbnail image with loading states and error handling.
 * Uses native img loading="lazy" and decoding="async" for performance.
 */
import { useState, useCallback } from 'react';
import { Spinner } from './Spinner';

interface ThumbnailProps {
  /** Model file ID to fetch thumbnail for. */
  modelFileId: string;
  /** Alt text for accessibility. */
  alt?: string;
  /** Optional CSS class name. */
  className?: string;
  /** Optional inline styles. */
  style?: React.CSSProperties;
}

const PLACEHOLDER_SVG = `data:image/svg+xml,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
  <rect width="800" height="600" fill="#e3e5ee"/>
  <text x="400" y="280" text-anchor="middle" font-family="system-ui" font-size="48" fill="#5a6072">3D</text>
  <text x="400" y="340" text-anchor="middle" font-family="system-ui" font-size="24" fill="#5a6072">Model</text>
</svg>
`)}`;

export const Thumbnail = ({
  modelFileId,
  alt = 'Model thumbnail',
  className,
  style,
}: ThumbnailProps) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const thumbnailUrl = `${baseUrl}/api/v1/files/${modelFileId}/thumbnail`;

  const handleLoad = useCallback(() => {
    setIsLoading(false);
    setHasError(false);
  }, []);

  const handleError = useCallback(() => {
    setIsLoading(false);
    setHasError(true);
  }, []);

  const containerStyle: React.CSSProperties = {
    position: 'relative',
    width: '100%',
    aspectRatio: '4 / 3',
    overflow: 'hidden',
    borderRadius: 'var(--radius-md)',
    background: 'var(--color-border)',
    ...style,
  };

  const imgStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    display: hasError ? 'none' : 'block',
  };

  const placeholderStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    display: hasError ? 'block' : 'none',
  };

  const loaderStyle: React.CSSProperties = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    display: isLoading && !hasError ? 'block' : 'none',
  };

  return (
    <div className={className} style={containerStyle}>
      {/* Loading skeleton */}
      <div style={loaderStyle}>
        <Spinner size={24} />
      </div>

      {/* Actual thumbnail */}
      <img
        src={thumbnailUrl}
        alt={alt}
        loading="lazy"
        decoding="async"
        onLoad={handleLoad}
        onError={handleError}
        style={imgStyle}
      />

      {/* Fallback placeholder */}
      <img
        src={PLACEHOLDER_SVG}
        alt=""
        aria-hidden="true"
        style={placeholderStyle}
      />
    </div>
  );
};
