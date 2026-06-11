FROM marlon360/usd-from-gltf:latest AS usd
FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DATA_ROOT=/data
ENV IFCCONVERT_PATH=/usr/local/bin/IfcConvert
ENV USD_FROM_GLTF_PATH=/usr/local/bin/usd_from_gltf
ENV BLENDER_PATH=/opt/blender/blender
ENV IFC_CONVERSION_TIMEOUT_S=120
ENV SKP_CONVERSION_TIMEOUT_S=180
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/local/ufg/lib:/usr/local/USDinst/lib
ENV PXR_PLUGINPATH_NAME=/usr/local/USDinst/lib/usd

ARG IFCONVERT_URL=https://s3.amazonaws.com/ifcopenshell-builds/IfcConvert-v0.7.11-d51fa2c-linux64.zip
ARG IFCONVERT_SHA256=b418e0f4c315a89199095b53e8f6b12804b60912f7f413a77ee79ca0e33da0b6

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    wget \
    unzip \
    xz-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libxi6 \
    libxxf86vm1 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

ARG BLENDER_VERSION=4.2.3
RUN set -eux; \
    wget -q --timeout=120 "https://download.blender.org/release/Blender4.2/blender-${BLENDER_VERSION}-linux-x64.tar.xz" -O /tmp/blender.tar.xz; \
    tar xf /tmp/blender.tar.xz -C /opt; \
    mv /opt/blender-* /opt/blender; \
    rm /tmp/blender.tar.xz; \
    /opt/blender/blender --version

COPY --from=usd /usr/local/ufg/bin/usd_from_gltf /usr/local/bin/usd_from_gltf
COPY --from=usd /usr/local/ufg/lib/ /usr/local/lib/
COPY --from=usd /usr/local/lib/ /usr/local/lib/
COPY --from=usd /usr/src/app/USDinst/ /usr/local/USDinst/

RUN set -eux; \
    wget -q --timeout=60 "$IFCONVERT_URL" -O /tmp/IfcConvert.zip && \
    echo "$IFCONVERT_SHA256  /tmp/IfcConvert.zip" | sha256sum -c - && \
    unzip /tmp/IfcConvert.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/IfcConvert && \
    rm /tmp/IfcConvert.zip && \
    IfcConvert --version && \
    usd_from_gltf --help >/dev/null 2>&1 || usd_from_gltf 2>&1 | head -1

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY converter_service.py usd_converter.py glb_normalize.py ifc_pipeline.py skp_to_glb.py skp_pipeline.py render_thumbnail.py .

RUN mkdir -p /data

EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=3 \
  CMD curl --fail http://localhost:8080/health || exit 1

CMD ["uvicorn", "converter_service:app", "--host", "0.0.0.0", "--port", "8080"]
