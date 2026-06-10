"""GLB → USDZ via Google's usd_from_gltf (Quick Look compatible)."""

from __future__ import annotations

import os
import subprocess

USD_FROM_GLTF_PATH = os.environ.get("USD_FROM_GLTF_PATH", "/usr/local/bin/usd_from_gltf")
CONVERSION_TIMEOUT_S = int(os.environ.get("CONVERSION_TIMEOUT_S", "120"))


class UsdConversionError(RuntimeError):
    pass


def glb_to_usdz(glb_path: str, usdz_path: str) -> None:
    if not os.path.isfile(glb_path) or os.path.getsize(glb_path) == 0:
        raise UsdConversionError("GLB input missing or empty")

    try:
        proc = subprocess.run(
            [USD_FROM_GLTF_PATH, glb_path, usdz_path],
            capture_output=True,
            text=True,
            timeout=CONVERSION_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as e:
        raise UsdConversionError("usd_from_gltf timeout") from e
    except FileNotFoundError as e:
        raise UsdConversionError("usd_from_gltf binary not found") from e

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:300]
        raise UsdConversionError(f"usd_from_gltf exited {proc.returncode}: {detail}")

    if not os.path.isfile(usdz_path) or os.path.getsize(usdz_path) == 0:
        raise UsdConversionError("usd_from_gltf produced empty USDZ")
