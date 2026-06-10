FROM --platform=linux/amd64 ubuntu:22.04
# ^ linux/amd64 is required because IfcOpenShell publishes only x86_64
#   linux64 binaries. On Apple Silicon (aarch64) hosts Docker Desktop will
#   transparently emulate amd64 via QEMU — build/run is slower but works.

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV IFCONVERT_PATH=/usr/local/bin/IfcConvert
# Pinned IfcConvert v0.7.11-d51fa2c build (latest stable linux64 on the
# IfcOpenShell S3 bucket as of 2026-06). If the SHA256 below does not match,
# the build will fail loudly rather than silently producing a container without
# the converter. Update the URL + SHA256 together when bumping the version.
ARG IFCONVERT_URL=https://s3.amazonaws.com/ifcopenshell-builds/IfcConvert-v0.7.11-d51fa2c-linux64.zip
ARG IFCONVERT_SHA256=b418e0f4c315a89199095b53e8f6b12804b60912f7f413a77ee79ca0e33da0b6

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    wget \
    unzip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hard-fail on download / SHA mismatch. No silent fallback that produces a
# container with no converter.
RUN set -eux; \
    wget -q --timeout=60 "$IFCONVERT_URL" -O /tmp/IfcConvert.zip && \
    echo "$IFCONVERT_SHA256  /tmp/IfcConvert.zip" | sha256sum -c - && \
    unzip /tmp/IfcConvert.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/IfcConvert && \
    rm /tmp/IfcConvert.zip && \
    IfcConvert --version || (echo "IfcConvert is not executable" && exit 1)

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY converter_service.py .

EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD curl --fail http://localhost:8080/health || exit 1

CMD ["uvicorn", "converter_service:app", "--host", "0.0.0.0", "--port", "8080"]
