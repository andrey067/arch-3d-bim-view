# Traefik with self-signed certs + dynamic TLS config baked in.
# Needed because the deploy targets a REMOTE docker context (ssh://homelab):
# bind-mounting local cert files does not work across the remote daemon, so we
# ship them inside the image instead.
FROM traefik:v3.3

COPY certs/ /certs/
COPY traefik/dynamic/ /dynamic/
