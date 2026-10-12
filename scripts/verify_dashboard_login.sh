#!/usr/bin/env bash
# verify_dashboard_login.sh — prove the credential works, and work out the reachable address.
set -u
U=hermes
P=H3GDSmZUEecNiXR7V7CplH0mgmTW84mf

echo "=== 1. does HTTP Basic with these credentials get past the gate? ==="
printf "  no creds      : HTTP %s (302 = redirected to sign-in)\n" \
  "$(curl -s -o /dev/null -w '%{http_code}' -m 10 http://127.0.0.1:4860/)"
printf "  with creds    : HTTP %s\n" \
  "$(curl -s -o /dev/null -w '%{http_code}' -m 10 -u "$U:$P" http://127.0.0.1:4860/)"
printf "  wrong creds   : HTTP %s (401/302 = rejected, which is what we want)\n" \
  "$(curl -s -o /dev/null -w '%{http_code}' -m 10 -u "$U:definitely-wrong" http://127.0.0.1:4860/)"
echo
echo "=== 2. what the authenticated page is ==="
curl -s -m 15 -u "$U:$P" http://127.0.0.1:4860/ | grep -oiE "<title>[^<]*</title>|(Profiles|Sessions|Memory|Channels|MCP|Webhooks)[^<]{0,20}" | head -8
echo
echo "=== 3. where this box sits ==="
echo "  route:    $(ip route 2>/dev/null | head -2 | tr '\n' ' ')"
echo "  /etc/hosts: $(grep -v '^#' /etc/hosts 2>/dev/null | tr '\n' ' ' | cut -c1-200)"
echo
echo "=== 4. any domain-ish names in this container's env ==="
tr '\0' '\n' < /proc/1/environ 2>/dev/null | grep -iE "domain|url|host|hstgr|cloud|srv1" | cut -d= -f1 | sort -u | head -12
