"""QR code generation using segno.

Generates a PNG QR code for the share link URL.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.features.conversion.pipelines.common import ConversionError

logger = logging.getLogger(__name__)


def generate_qr(url: str, output_path: Path, *, scale: int = 10) -> None:
    """Generate a QR code PNG for the given URL.

    Args:
        url: The URL to encode in the QR code.
        output_path: Destination path for the .png output.
        scale: QR code scale factor (default 10).

    Raises:
        ConversionError: If generation fails.
    """
    try:
        import segno

        qr = segno.make(url)
        qr.save(str(output_path), scale=scale, border=2)

    except Exception as exc:
        raise ConversionError(
            f"QR generation failed: {exc}", stage="qr_generate"
        ) from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ConversionError(
            "QR output is empty or missing.",
            stage="qr_export",
        )

    logger.info("QR generated: %s (%d bytes)", output_path.name, output_path.stat().st_size)
