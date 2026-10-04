#!/usr/bin/env bash
# Check the two image risks that structural tests can't see:
#   1. every generated SVG is well-formed XML (so browsers render it)
#   2. the hotlinked key art / headshots actually return HTTP 200 from this network
# Run: bash scripts/check_images.sh
set -u
cd "$(dirname "$0")/.."

echo "1. generated SVG validity"
python3 - <<'PY'
import json, pathlib, xml.etree.ElementTree as ET
art = pathlib.Path("assets/art")
bad, good = [], 0
for f in sorted(art.glob("*.svg")):
    try:
        ET.parse(f); good += 1
    except ET.ParseError as e:
        bad.append((f.name, str(e)))
print(f"  {good} SVG files parse as XML")
for name, err in bad:
    print(f"  ✗ {name}: {err}")
print("  OK" if not bad else f"  {len(bad)} INVALID")
PY

echo
echo "2. hotlinked images return 200 (poster + headshots from the probe file)"
python3 - <<'PY' > /tmp/dw_hotlinks.txt
import json, pathlib
d = json.loads(pathlib.Path("research/raw/image_sources.json").read_text())
urls = []
for term, hits in d.get("imdb", {}).items():
    if hits and hits[0].get("image"):
        urls.append((term, hits[0]["image"]))
for term, url in urls[:8]:
    print(f"{term}\t{url}")
PY
while IFS=$'\t' read -r term url; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 20 -A "Mozilla/5.0" "$url")
  printf "  %-22s HTTP %s\n" "$term" "$code"
done < /tmp/dw_hotlinks.txt

echo
echo "3. committed image weight"
du -sh assets/art assets/img/commons 2>/dev/null
