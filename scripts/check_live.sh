#!/usr/bin/env bash
# Verify the deployed GitHub Pages site (V1 + V2). Retries while the build finishes.
# Run: bash scripts/check_live.sh
set -u
BASE="https://joenobody-ai.github.io/different-world-notes/"

echo "waiting for the deployed build"
for i in 1 2 3 4 5 6 7 8 9 10; do
  code=$(curl -s -o /tmp/dw_live.html -w "%{http_code}" -m 20 "$BASE")
  echo "  attempt $i: HTTP $code ($(wc -c < /tmp/dw_live.html) bytes)"
  [ "$code" = "200" ] && break
  sleep 20
done

echo
echo "V1"
printf "  homepage: %s episode cards, %s index rows\n" \
  "$(grep -c 'data-episode-card' /tmp/dw_live.html)" "$(grep -c '<tr data-tier=' /tmp/dw_live.html)"
for p in ep01.html ep07.html ep10.html index.html; do
  c=$(curl -s -o /tmp/p.html -w '%{http_code}' -m 20 "$BASE$p")
  printf "  %-12s HTTP %s  %s bytes  %s callback cards\n" "$p" "$c" "$(wc -c < /tmp/p.html)" "$(grep -c 'article class="cb"' /tmp/p.html || true)"
done

echo
echo "V2 (Netflix-style)"
c=$(curl -s -o /tmp/v2.html -w '%{http_code}' -m 20 "$BASE"v2/)
printf "  %-12s HTTP %s  %s bytes  %s shelves  %s ranked cards\n" "v2/" "$c" "$(wc -c < /tmp/v2.html)" \
  "$(grep -c 'class="shelf"' /tmp/v2.html)" "$(grep -c 'class="card rank"' /tmp/v2.html)"
for p in ep01.html ep05.html ep10.html; do
  c=$(curl -s -o /tmp/v2p.html -w '%{http_code}' -m 20 "$BASE"v2/$p)
  printf "  v2/%-9s HTTP %s  %s bytes  %s callback rows\n" "$p" "$c" "$(wc -c < /tmp/v2p.html)" "$(grep -c 'class="ep-row"' /tmp/v2p.html || true)"
done

echo
echo "assets"
for a in assets/v2/netflix.css assets/v2/netflix.js assets/art/hero.svg assets/art/ep07.svg; do
  c=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "$BASE$a")
  printf "  %-28s HTTP %s\n" "$a" "$c"
done
