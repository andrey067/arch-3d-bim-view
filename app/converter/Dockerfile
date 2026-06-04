FROM ubuntu:22.04

# Install IfcOpenShell and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install IfcOpenShell (IfcConvert)
# Download pre-built binary
RUN wget -q https://s3.amazonaws.com/ifcopenshell-builds/IfcConvert-linux64.zip \
    && unzip IfcConvert-linux64.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/IfcConvert \
    && rm IfcConvert-linux64.zip

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    minio>=7.0.0 \
    psycopg2-binary>=2.9.0

WORKDIR /app
COPY converter.py .

CMD ["python3", "converter.py"]