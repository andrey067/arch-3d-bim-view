# Arch3DAR Backend — Open access MVP
# Includes: Python 3.13, FastAPI, trimesh, pycollada, IfcConvert, usd_from_gltf, assimp
FROM python:3.13-slim AS base

WORKDIR /app

# System deps (Debian 13 "trixie": use libgl1 — libgl1-mesa-glx was removed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        ca-certificates \
        wget \
        unzip \
        assimp-utils \
    && rm -rf /var/lib/apt/lists/*

# IfcConvert (IfcOpenShell) — IFC → GLB. Pinned build + SHA256 (hard-fail on mismatch).
ARG IFCONVERT_URL=https://s3.amazonaws.com/ifcopenshell-builds/IfcConvert-v0.7.11-d51fa2c-linux64.zip
ARG IFCONVERT_SHA256=b418e0f4c315a89199095b53e8f6b12804b60912f7f413a77ee79ca0e33da0b6
RUN wget -q --timeout=60 "$IFCONVERT_URL" -O /tmp/ifcconvert.zip && \
    echo "$IFCONVERT_SHA256  /tmp/ifcconvert.zip" | sha256sum -c - && \
    unzip -q /tmp/ifcconvert.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/IfcConvert && \
    rm /tmp/ifcconvert.zip

# usd_from_gltf source image (GLB -> USDZ for iOS AR). Binary in /usr/local/ufg/bin,
# links USD shared libs in /usr/local/usd/lib.
FROM leon/usd-from-gltf:latest AS usd

FROM base AS runtime

# Bring USD runtime + ufg converter (both under /usr/local in the source image)
COPY --from=usd /usr/local/usd /usr/local/usd
COPY --from=usd /usr/local/ufg /usr/local/ufg

# Put usd_from_gltf on PATH and resolve its shared libs / python plugins
ENV PATH="/usr/local/usd/bin:/usr/local/ufg/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/usd/lib:/usr/local/ufg/lib"
ENV PYTHONPATH="/usr/local/usd/lib/python:/usr/local/ufg/python"

# uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Fail-hard: every conversion tool must be present and dynamically link
RUN IfcConvert --version && \
    assimp version && \
    if ldd /usr/local/ufg/bin/usd_from_gltf | grep -q "not found"; then \
        echo "ERROR: usd_from_gltf has unresolved libraries:"; \
        ldd /usr/local/ufg/bin/usd_from_gltf | grep "not found"; \
        exit 1; \
    fi && \
    command -v usd_from_gltf

# Python deps (frozen against uv.lock)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# Application code
COPY app/ app/

# Storage directories
RUN mkdir -p /app/storage/originals /app/storage/converted /app/storage/usdz /app/storage/qr

# Runtime config
ENV IFCCONVERT_PATH=/usr/local/bin/IfcConvert
ENV USD_FROM_GLTF_PATH=usd_from_gltf
ENV STORAGE_ROOT=/app/storage
ENV DATABASE_URL=sqlite:////app/storage/app.db

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
