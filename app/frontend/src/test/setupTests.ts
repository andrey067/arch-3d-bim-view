import '@testing-library/jest-dom/vitest';

if (!customElements.get('model-viewer')) {
  class ModelViewerStub extends HTMLElement {}
  customElements.define('model-viewer', ModelViewerStub);
}
