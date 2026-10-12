#!/usr/bin/env bash
# find_login_endpoint.sh — the form has no action, so the endpoint is in the JS bundle. Find and test it.
set -u
U=hermes
P=H3GDSmZUEecNiXR7V7CplH0mgmTW84mf
D=/opt/hermes/hermes_cli/web_dist
J=/tmp/c2.txt

echo "=== auth-ish endpoints referenced in the dashboard bundle ==="
grep -rhoE '"/[a-z0-9_./-]*(auth|login|session|signin|basic)[a-z0-9_./-]*"' "$D" 2>/dev/null | sort -u | head -20
echo
echo "=== fetch/POST calls near the basic provider ==="
grep -rhoE 'fetch\("[^"]{0,60}"|fetch\(`[^`]{0,60}`|/auth/[a-z0-9_/-]+' "$D" 2>/dev/null | sort -u | head -20

echo
echo "=== try the likely endpoints ==="
for ep in /auth/basic /login/basic /api/login /api/auth/basic /auth/login /session; do
  code=$(curl -s -o /tmp/r.html -w '%{http_code}' -m 15 -c "$J" -X POST "http://127.0.0.1:4860$ep" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$U\",\"password\":\"$P\"}")
  echo "  POST $ep (json) -> HTTP $code"
  if [ "$code" = "200" ] || [ "$code" = "302" ]; then
    echo "     body: $(head -c 120 /tmp/r.html | tr -d '\n')"
    echo "     cookies: $(awk '{print $6}' "$J" 2>/dev/null | paste -sd, -)"
    printf "     then GET / -> HTTP %s\n" "$(curl -s -o /tmp/h.html -w '%{http_code}' -m 15 -b "$J" http://127.0.0.1:4860/)"
    break
  fi
done
