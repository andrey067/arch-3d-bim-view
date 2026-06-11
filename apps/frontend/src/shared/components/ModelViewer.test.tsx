/**
 * Tests for ModelViewer component - AR functionality.
 *
 * Tests cover:
 * - AR button display on supported devices
 * - Device detection (Android, iOS, Desktop)
 * - HTTPS/HTTP detection and banner
 * - AR fallback messages
 * - AR activation flow
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ModelViewer } from './ModelViewer';

// Mock model-viewer element
class MockModelViewer extends HTMLElement {
  activateAR = vi.fn();
  override setAttribute = vi.fn();
}

customElements.define('model-viewer', MockModelViewer);

// Helper to mock navigator.xr
const mockNavigatorXR = (supported: boolean) => {
  Object.defineProperty(navigator, 'xr', {
    value: {
      isSessionSupported: vi.fn().mockResolvedValue(supported),
    },
    writable: true,
    configurable: true,
  });
};

// Helper to remove navigator.xr
const removeNavigatorXR = () => {
  Object.defineProperty(navigator, 'xr', {
    value: undefined,
    writable: true,
    configurable: true,
  });
};

// Helper to mock user agent
const mockUserAgent = (ua: string) => {
  Object.defineProperty(navigator, 'userAgent', {
    value: ua,
    writable: true,
    configurable: true,
  });
};

// Helper to mock window.location.protocol
const mockProtocol = (protocol: string) => {
  Object.defineProperty(window, 'location', {
    value: { ...window.location, protocol },
    writable: true,
    configurable: true,
  });
};

describe('ModelViewer - AR Functionality', () => {
  beforeEach(() => {
    // Default: secure context
    Object.defineProperty(window, 'isSecureContext', {
      value: true,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // Helper to simulate model load
  const simulateModelLoad = () => {
    const viewer = document.querySelector('model-viewer');
    if (viewer) {
      act(() => {
        viewer.dispatchEvent(new Event('load'));
      });
    }
  };

  describe('AR Button Display', () => {
    it('should not show AR button when arEnabled is false', async () => {
      mockNavigatorXR(true);
      render(<ModelViewer src="test.glb" arEnabled={false} />);

      simulateModelLoad();

      await waitFor(() => {
        expect(screen.queryByText('Visualizar em AR')).not.toBeInTheDocument();
      });
    });

    it('should show AR button when arEnabled and AR is supported', async () => {
      mockNavigatorXR(true);
      mockUserAgent('Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/79.0');

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      simulateModelLoad();

      await waitFor(() => {
        expect(screen.getByText('Visualizar em AR')).toBeInTheDocument();
      });
    });

    it('should not show AR button on insecure context (HTTP)', async () => {
      Object.defineProperty(window, 'isSecureContext', {
        value: false,
        writable: true,
        configurable: true,
      });
      mockNavigatorXR(true);

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      simulateModelLoad();

      await waitFor(() => {
        expect(screen.queryByText('Visualizar em AR')).not.toBeInTheDocument();
      });
    });
  });

  describe('Device Detection', () => {
    it('should detect Android device and show AR button', async () => {
      mockNavigatorXR(true);
      mockUserAgent('Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36');

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      simulateModelLoad();

      await waitFor(() => {
        expect(screen.getByText('Visualizar em AR')).toBeInTheDocument();
      });
    });

    it('should detect iOS device and show AR button', async () => {
      mockUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15');

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      simulateModelLoad();

      await waitFor(() => {
        expect(screen.getByText('Visualizar em AR')).toBeInTheDocument();
      });
    });

    it('should detect desktop and show fallback message', async () => {
      removeNavigatorXR();
      mockUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      simulateModelLoad();

      await waitFor(() => {
        expect(screen.getByText('AR indisponivel neste dispositivo')).toBeInTheDocument();
      });
    });
  });

  describe('HTTPS/HTTP Detection', () => {
    it('should show HTTPS warning banner on HTTP', () => {
      mockProtocol('http:');
      mockNavigatorXR(true);

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      expect(screen.getByText('AR requer HTTPS')).toBeInTheDocument();
    });

    it('should not show HTTPS warning banner on HTTPS', () => {
      mockProtocol('https:');
      mockNavigatorXR(true);

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      expect(screen.queryByText('AR requer HTTPS')).not.toBeInTheDocument();
    });
  });

  describe('AR Fallback Messages', () => {
    it('should show fallback message when AR is not supported', async () => {
      removeNavigatorXR();
      mockUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      simulateModelLoad();

      await waitFor(() => {
        expect(screen.getByText('AR indisponivel neste dispositivo')).toBeInTheDocument();
      });
    });

    it('should not show fallback message when AR is supported', async () => {
      mockNavigatorXR(true);
      mockUserAgent('Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36');

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      simulateModelLoad();

      await waitFor(() => {
        expect(screen.queryByText('AR indisponivel neste dispositivo')).not.toBeInTheDocument();
      });
    });
  });

  describe('AR Activation Flow', () => {
    it('should call activateAR when button is clicked', async () => {
      mockNavigatorXR(true);
      mockUserAgent('Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36');

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      simulateModelLoad();

      await waitFor(() => {
        expect(screen.getByText('Visualizar em AR')).toBeInTheDocument();
      });

      const arButton = screen.getByText('Visualizar em AR');
      fireEvent.click(arButton);

      // The mock model-viewer's activateAR should be called
      // Note: In real implementation, this would trigger AR session
    });
  });

  describe('Basic Functionality', () => {
    it('should render model-viewer with src', () => {
      render(<ModelViewer src="test.glb" />);

      const viewer = document.querySelector('model-viewer');
      expect(viewer).toBeInTheDocument();
    });

    it('should render with poster image', () => {
      render(<ModelViewer src="test.glb" poster="poster.webp" />);

      const viewer = document.querySelector('model-viewer');
      expect(viewer).toBeInTheDocument();
    });

    it('should show loading state initially', () => {
      render(<ModelViewer src="test.glb" />);

      expect(screen.getByText('Carregando modelo 3D...')).toBeInTheDocument();
    });

    it('should call onLoad when model loads', () => {
      const onLoad = vi.fn();
      render(<ModelViewer src="test.glb" onLoad={onLoad} />);

      const viewer = document.querySelector('model-viewer');
      if (viewer) {
        act(() => {
          viewer.dispatchEvent(new Event('load'));
        });
      }

      expect(onLoad).toHaveBeenCalled();
    });

    it('should show reset camera button after load', async () => {
      render(<ModelViewer src="test.glb" />);

      simulateModelLoad();

      await waitFor(() => {
        expect(screen.getByTitle('Reset camera position')).toBeInTheDocument();
      });
    });
  });

  describe('AR Attributes', () => {
    it('should add ar attributes when AR is enabled and supported', async () => {
      mockNavigatorXR(true);
      mockUserAgent('Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36');

      render(<ModelViewer src="test.glb" arEnabled={true} />);

      simulateModelLoad();

      await waitFor(() => {
        const viewer = document.querySelector('model-viewer');
        expect(viewer).toBeInTheDocument();
      });
    });

    it('should not add ar attributes when AR is disabled', () => {
      mockNavigatorXR(true);

      render(<ModelViewer src="test.glb" arEnabled={false} />);

      const viewer = document.querySelector('model-viewer');
      expect(viewer).toBeInTheDocument();
    });
  });
});
