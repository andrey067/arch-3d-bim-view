"""Pure functions that derive storage keys from project/model IDs.

Keys are **always relative** to the storage root.  Layout matches
``data-model.md §layout físico``::

    originals/<project_id>/<model_file_id>__<sanitized_filename>
    converted/<project_id>/<model_file_id>.glb
    thumbnails/<project_id>/<model_file_id>.webp
"""
from __future__ import annotations

import re

_MAX_FILENAME_LEN = 255
_SANITIZE_RE = re.compile(r'[/\\:\x00]')


def _sanitize_filename(name: str) -> str:
    """Remove path separators and null bytes; truncate to filesystem limits."""
    clean = _SANITIZE_RE.sub("_", name)
    if len(clean) > _MAX_FILENAME_LEN:
        clean = clean[:_MAX_FILENAME_LEN]
    return clean


def original_key(project_id: str, model_file_id: str, filename: str) -> str:
    """Return the storage key for an uploaded original file."""
    safe_name = _sanitize_filename(filename)
    return f"originals/{project_id}/{model_file_id}__{safe_name}"


def glb_key(project_id: str, model_file_id: str) -> str:
    """Return the storage key for a converted GLB file."""
    return f"converted/{project_id}/{model_file_id}.glb"


def thumbnail_key(project_id: str, model_file_id: str) -> str:
    """Return the storage key for a generated thumbnail."""
    return f"thumbnails/{project_id}/{model_file_id}.webp"
