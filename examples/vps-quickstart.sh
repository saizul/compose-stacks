#!/usr/bin/env bash
# Fresh VPS: Caddy (HTTPS) in front of WordPress and Uptime Kuma.
#
#   DOMAIN=blog.example.com STATUS_DOMAIN=status.example.com EMAIL=you@example.com ./vps-quickstart.sh
#
# Requirements: Docker with Compose v2, compose-stacks, DNS records for both
# domains pointing at this server, ports 80 and 443 open.
set -euo pipefail

: "${DOMAIN:?set DOMAIN}"
: "${STATUS_DOMAIN:?set STATUS_DOMAIN}"
: "${EMAIL:?set EMAIL}"
BASE="${BASE:-/opt/stacks}"

# Shared network so Caddy reaches the apps by service name.
docker network inspect web >/dev/null 2>&1 || docker network create web

compose-stacks init wordpress "$BASE/wordpress"
compose-stacks init uptime-kuma "$BASE/uptime-kuma"
compose-stacks init caddy "$BASE/caddy" --set ACME_EMAIL="$EMAIL" --set SITE_DOMAIN="$DOMAIN" --set UPSTREAM=wordpress:80

# Attach the services to the shared network with override files.
cat > "$BASE/wordpress/compose.override.yaml" <<'YAML'
services:
  wordpress:
    networks: [default, backend, web]
networks:
  web:
    external: true
YAML

cat > "$BASE/uptime-kuma/compose.override.yaml" <<'YAML'
services:
  uptime-kuma:
    networks: [default, web]
networks:
  web:
    external: true
YAML

cat > "$BASE/caddy/compose.override.yaml" <<'YAML'
services:
  caddy:
    networks: [default, web]
networks:
  web:
    external: true
YAML

cat >> "$BASE/caddy/Caddyfile" <<CADDY

$STATUS_DOMAIN {
	reverse_proxy uptime-kuma:3001
}
CADDY

for stack in wordpress uptime-kuma caddy; do
  (cd "$BASE/$stack" && docker compose up -d)
done

echo "Done. Open https://$DOMAIN and https://$STATUS_DOMAIN"
