#!/usr/bin/env bash
# hermes_dashboard_auth.sh — how does the running dashboard authenticate, and what login options exist?
set -u
mask() { sed -E 's/([A-Za-z0-9_\-]{6})[A-Za-z0-9_\-]{10,}/\1…<masked>/g'; }

echo "=== dashboard process + its auth-related env ==="
tr '\0' '\n' < /proc/131/environ 2>/dev/null | grep -iE "hermes|auth|token|password|secret|portal" | mask | head -20
echo
echo "=== dashboard help (auth/token flags) ==="
hermes dashboard --help 2>&1 | grep -iE "auth|token|password|host|port|login|gate|secret" | head -20
echo
echo "=== full config.yaml (secrets masked) ==="
mask < /opt/data/config.yaml
echo
echo "=== credential stores ==="
for f in /opt/data/auth.json /opt/data/.env /opt/data/profiles/tax-time/auth.json /opt/data/profiles/tax-time/.env; do
  if [ -f "$f" ]; then echo "--- $f"; mask < "$f" | head -20; else echo "(absent) $f"; fi
done
echo
echo "=== dashboard startup lines in the logs (looking for a printed URL/token) ==="
grep -rhiE "dashboard" /opt/data/logs/*.log 2>/dev/null | mask | tail -12
echo
echo "=== login / auth / portal help ==="
hermes login --help 2>&1 | head -12
hermes auth --help 2>&1 | head -12
hermes portal --help 2>&1 | head -14
