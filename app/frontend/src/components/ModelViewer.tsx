import { useEffect, useState } from 'react';

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          src?: string;
          alt?: string;
          poster?: string;
          ar?: boolean | '';
          'ar-modes'?: string;
          'camera-controls'?: boolean | '';
          autoplay?: boolean | '';
          'shadow-intensity'?: string | number;
        },
        HTMLElement
      >;
    }
  }
}

export {};

export interface ModelViewerProps {
  glbUrl: string;
  thumbnailUrl: string;
  alt: string;
}

export default function ModelViewer({ glbUrl, thumbnailUrl, alt }: ModelViewerProps) {
  const [isArCapable, setIsArCapable] = useState(false);
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
    const ua = navigator.userAgent || '';
    const isAndroid = /Android/i.test(ua);
    const isIos = /iPhone|iPad|iPod/i.test(ua);
    setIsArCapable(isAndroid || isIos);
  }, []);

  const arAttributes: Record<string, string | boolean> = isArCapable
    ? {
        ar: true,
        'ar-modes': 'webxr scene-viewer quick-look',
      }
    : { ar: false };

  return (
    <model-viewer
      src={glbUrl}
      alt={alt}
      poster={thumbnailUrl}
      camera-controls
      autoplay
      shadow-intensity="1"
      style={{ width: '100%', height: '100%', backgroundColor: '#f5f5f5' }}
      {...arAttributes}
      data-testid="model-viewer"
      data-ar-capable={hasMounted ? String(isArCapable) : 'false'}
    />
  );
}
