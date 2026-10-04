#!/usr/bin/env bash
# Verify the deployed GitHub Pages site (retries while the build finishes).
set -u
URL="https://joenobody-ai.github.io/different-world-notes/"
for i in 1 2 3 4 5 6 7 8; do
  code=$(curl -s -o /tmp/dw_live.html -w "%{http_code}" -m 20 "$URL")
  bytes=$(wc -c < /tmp/dw_live.html)
  echo "attempt $i: HTTP $code  bytes=$bytes"
  if [ "$code" = "200" ]; then break; fi
  sleep 20
done
echo "=== live content checks ==="
echo "homepage: $(grep -c 'data-episode-card' /tmp/dw_live.html) episode cards, $(grep -c '<tr data-tier=' /tmp/dw_live.html) index rows"
grep -o 'Premiered 24 Sep 2026[^<]*' /tmp/dw_live.html | head -1
grep -o 'A Gift &amp; The Curse' /tmp/dw_live.html | head -1
for p in ep01.html ep05.html ep07.html ep10.html assets/styles.css assets/app.js; do
  c=$(curl -s -o /tmp/p.html -w '%{http_code}' -m 20 "$URL$p")
  cards=$(grep -c 'article class="cb"' /tmp/p.html || true)
  echo "  $p -> HTTP $c, $(wc -c < /tmp/p.html) bytes, $cards callback cards"
done
