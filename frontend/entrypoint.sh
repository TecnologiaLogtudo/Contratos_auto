#!/bin/sh
set -eu

echo "[frontend] startup diagnostics"
echo "[frontend] VITE_APP_BASE_PATH=${VITE_APP_BASE_PATH:-}"
echo "[frontend] VITE_API_BASE_URL=${VITE_API_BASE_URL:-}"
echo "[frontend] listing /usr/share/nginx/html/contratos"
ls -la /usr/share/nginx/html/contratos || true
echo "[frontend] listing /usr/share/nginx/html/contratos/assets"
ls -la /usr/share/nginx/html/contratos/assets || true
echo "[frontend] index.html (first 40 lines)"
sed -n '1,40p' /usr/share/nginx/html/contratos/index.html || true

exec nginx -g "daemon off;"
