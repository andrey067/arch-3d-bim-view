#!/usr/bin/env bash
set -euo pipefail

# Generate self-signed TLS certificates for the homelab deployment.
# Usage: ./generate-certs.sh [IP_ADDRESS]
#
# Defaults to 192.168.68.51 if no argument is provided.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERT_DIR="${SCRIPT_DIR}/certs"
IP="${1:-192.168.68.51}"

mkdir -p "$CERT_DIR"

if [[ -f "${CERT_DIR}/tls.crt" && -f "${CERT_DIR}/tls.key" ]]; then
  echo "Certificates already exist in ${CERT_DIR}. Skipping."
  echo "  To regenerate, delete ${CERT_DIR}/tls.crt and ${CERT_DIR}/tls.key first."
  exit 0
fi

echo "Generating self-signed certificate for IP: ${IP}"

openssl req -x509 -nodes -days 3650 \
  -newkey rsa:2048 \
  -keyout "${CERT_DIR}/tls.key" \
  -out "${CERT_DIR}/tls.crt" \
  -subj "/CN=${IP}" \
  -addext "subjectAltName=IP:${IP}"

chmod 644 "${CERT_DIR}/tls.crt"
chmod 600 "${CERT_DIR}/tls.key"

echo "Certificates generated:"
echo "  ${CERT_DIR}/tls.crt"
echo "  ${CERT_DIR}/tls.key"
echo ""
echo "Valid for 3650 days (~10 years). SAN: IP:${IP}"
