#!/usr/bin/env bash
# show_dashboard_login.sh — the dashboard's admin credentials and the address it is listening on.
set -u
echo "=== admin credentials (from the running dashboard process) ==="
tr '\0' '\n' < /proc/131/environ 2>/dev/null | grep -E "^(ADMIN_USERNAME|ADMIN_PASSWORD|HERMES_WEB_|HERMES_DASHBOARD|HERMES_HOST|HERMES_PORT)" | sort
echo
echo "=== every HERMES_* env key name (values hidden unless auth-related) ==="
tr '\0' '\n' < /proc/131/environ 2>/dev/null | grep '^HERMES' | cut -d= -f1 | sort -u
echo
echo "=== where this container sits on the network ==="
hostname -I 2>/dev/null
hostname 2>/dev/null
echo
echo "=== is the port reachable locally? ==="
curl -s -o /dev/null -w "http://127.0.0.1:4860  -> HTTP %{http_code}\n" -m 10 http://127.0.0.1:4860/ || echo "curl failed"
curl -s -m 10 http://127.0.0.1:4860/ | head -c 400
echo
echo
echo "=== does the login page ask for the password or an OAuth provider? ==="
curl -s -m 10 http://127.0.0.1:4860/login | grep -oiE "(password|oauth|sign in|username|portal)[^<\"]{0,40}" | head -8
