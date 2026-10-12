#!/usr/bin/env bash
# hermes_auth_recon.sh — what auth/login surfaces exist for this Hermes install?
set -u
echo "=== hermes binary + version ==="
command -v hermes || echo "(hermes not on PATH)"
hermes --version 2>&1 | head -2
echo
echo "=== config files ==="
ls -la /opt/data/config.yaml /opt/data/profiles/tax-time/config.yaml 2>/dev/null
find /opt/data -maxdepth 3 -name "config.yaml" -not -path "*/node_modules/*" 2>/dev/null | head -10
echo
echo "=== auth-ish keys in config (values masked) ==="
python3 - <<'PY'
import glob, re, pathlib
keys = ("password", "passwd", "login", "token", "api_key", "apikey", "secret", "auth",
        "user", "username", "portal", "gateway", "web_", "host", "port", "url")
for f in ["/opt/data/config.yaml", "/opt/data/profiles/tax-time/config.yaml",
          "/opt/data/profiles/different-world/config.yaml"]:
    p = pathlib.Path(f)
    if not p.exists():
        continue
    print(f"--- {f}")
    for i, line in enumerate(p.read_text().splitlines(), 1):
        low = line.lower()
        if any(k in low for k in keys) and line.strip() and not line.strip().startswith("#"):
            masked = re.sub(r"(gho_|sk-|nous-|eyJ)[A-Za-z0-9_\-\.]{8,}", r"\1<masked>", line)
            print(f"  {i:>4}: {masked[:150]}")
PY
echo
echo "=== running hermes-ish processes ==="
ps -eo pid,etime,cmd 2>/dev/null | grep -iE "hermes|gateway|uvicorn|node .*hermes" | grep -v grep | head -10
echo
echo "=== listening ports ==="
(ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | head -20
echo
echo "=== hermes CLI subcommands mentioning auth/login ==="
hermes --help 2>&1 | grep -iE "auth|login|logout|account|portal|web|serve|gateway|token" | head -20
