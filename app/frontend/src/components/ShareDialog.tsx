import { useState } from 'react';

export interface ShareDialogProps {
  open: boolean;
  publicUrl: string;
  qrCodeUrl: string;
  onClose: () => void;
}

export default function ShareDialog({ open, publicUrl, qrCodeUrl, onClose }: ShareDialogProps) {
  const [copied, setCopied] = useState(false);

  if (!open) return null;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(publicUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" data-testid="share-dialog">
      <div className="modal card">
        <h2>Share</h2>
        <p>Send this link to your client, or share the QR code.</p>
        <div className="share-row">
          <input value={publicUrl} readOnly aria-label="Public URL" />
          <button className="button" onClick={copy} data-testid="copy-link">
            {copied ? 'Copied!' : 'Copy link'}
          </button>
        </div>
        <div className="qr-wrap">
          <img src={qrCodeUrl} alt="QR code" data-testid="qr-code" />
        </div>
        <button className="button primary" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
