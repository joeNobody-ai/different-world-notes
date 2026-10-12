#!/usr/bin/env bash
# probe_blocked.sh — are the 403s a dead link, or a WAF blocking an automated client?
# Sends a full browser-like header set. If the page returns 200 with browser headers but 403 without,
# it is a bot block (the link is fine for a human), and that is what we will say in the bibliography.
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
for u in \
  "https://nmaahc.si.edu/" \
  "https://www.loc.gov/collections/civil-rights-history-project/" \
  "https://www.loc.gov/" \
  "https://www.wdl.org/" \
  "https://www.annualreviews.org/journal/soc" \
  "https://sites.ed.gov/whhbcu/" \
  "https://www.bls.gov/" \
  "https://www.si.edu/" ; do
  plain=$(curl -s -o /dev/null -w '%{http_code}' -L -m 20 "$u")
  browser=$(curl -s -o /dev/null -w '%{http_code}' -L -m 25 -A "$UA" \
     -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' \
     -H 'Accept-Language: en-US,en;q=0.9' \
     -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Upgrade-Insecure-Requests: 1' "$u")
  printf "plain=%-4s browser=%-4s %s\n" "$plain" "$browser" "$u"
done
