#!/usr/bin/env bash
# test_login_flow.sh — find the sign-in form, submit it, and confirm we land inside the dashboard.
set -u
U=hermes
P=H3GDSmZUEecNiXR7V7CplH0mgmTW84mf
J=/tmp/hermes_cookies.txt
rm -f "$J"

echo "=== sign-in form: action, method, field names ==="
curl -s -m 15 http://127.0.0.1:4860/login -o /tmp/login.html
grep -oiE '<form[^>]*>' /tmp/login.html | head -4
grep -oiE 'name="[^"]+"' /tmp/login.html | sort -u | head -10
echo

echo "=== submit the form ==="
code=$(curl -s -o /tmp/post.html -w '%{http_code}' -m 20 -c "$J" \
  -X POST http://127.0.0.1:4860/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=$U" --data-urlencode "password=$P")
echo "  POST /login -> HTTP $code"
echo "  cookies set: $(grep -c . "$J" 2>/dev/null) $(awk '{print $6}' "$J" 2>/dev/null | paste -sd, -)"
echo

echo "=== can we now load the dashboard with that session? ==="
printf "  GET / with cookie -> HTTP %s\n" "$(curl -s -o /tmp/home.html -w '%{http_code}' -m 20 -b "$J" http://127.0.0.1:4860/)"
grep -oiE '<title>[^<]*</title>' /tmp/home.html | head -2
grep -oiE '(Profiles|Sessions|Memory|Channels|MCP|Webhooks|Chat|Config)[a-z ]{0,15}' /tmp/home.html | sort -u | head -10
echo
echo "=== a wrong password for contrast ==="
printf "  POST /login (bad pw) -> HTTP %s\n" "$(curl -s -o /dev/null -w '%{http_code}' -m 20 \
  -X POST http://127.0.0.1:4860/login -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=$U" --data-urlencode "password=nope")"
