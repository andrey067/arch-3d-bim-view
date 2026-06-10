import { describe, it, expect } from 'vitest';

const FORBIDDEN: Array<{ pattern: RegExp; label: string }> = [
  { pattern: /from\s+['"]\.\.\/components\/ModelViewer['"]/, label: "import '../components/ModelViewer'" },
  { pattern: /from\s+['"]\.\.\/auth\/useArCapability['"]/, label: "import '../auth/useArCapability'" },
  { pattern: /from\s+['"]@google\/model-viewer['"]/, label: "import '@google/model-viewer'" },
  { pattern: /<model-viewer\b/, label: '<model-viewer> JSX element' },
];

const adminPages = import.meta.glob<string>('../pages/*.tsx', {
  query: '?raw',
  import: 'default',
  eager: true,
});

const ADMIN_FILES = [
  '../pages/DashboardPage.tsx',
  '../pages/ProjectDetailPage.tsx',
  '../pages/UploadPage.tsx',
  '../pages/NotFoundPage.tsx',
];

describe('admin pages must not depend on the 3D viewer or AR capability', () => {
  it.each(ADMIN_FILES)('%s has no model-viewer / AR imports', (key) => {
    const source = adminPages[key];
    expect(source, `${key} should be discoverable via import.meta.glob`).toBeTypeOf('string');
    for (const { pattern, label } of FORBIDDEN) {
      expect(source!, `${key} must not contain ${label}`).not.toMatch(pattern);
    }
  });
});
