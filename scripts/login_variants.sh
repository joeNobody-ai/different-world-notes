#!/usr/bin/env bash
# login_variants.sh — try the form-encoded variants the dashboard's sign-in page would use.
set -u
U=hermes
P=H3GDSmZUEecNiXR7V7CplH0mgmTW84mf
for ep in /auth/basic /api/auth/basic /auth/login /api/auth/login /auth/session; do
  rm -f /tmp/j.txt
  out=$(curl -s -o /tmp/o.html -w '%{http_code}|%{redirect_url}' -m 15 -c /tmp/j.txt -D /tmp/hd.txt \
    -X POST "http://127.0.0.1:4860$ep" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "username=$U" --data-urlencode "password=$P" --data-urlencode "next=/")
  echo "POST $ep (form) -> $out"
  echo "   set-cookie: $(grep -i '^set-cookie' /tmp/hd.txt | cut -d: -f2- | cut -d= -f1 | paste -sd, -)"
  echo "   allow: $(grep -i '^allow' /tmp/hd.txt | paste -sd, -)"
  body=$(head -c 100 /tmp/o.html | tr -d '\n')
  [ -n "$body" ] && echo "   body: $body"
done
echo
echo "=== the sign-in page's own script: what does it do on submit? ==="
grep -oE '(action|method|provider|api)[^,;]{0,60}' /tmp/login.html 2>/dev/null | head -12
