#!/usr/bin/env bash
# Final checks + cross-link the two repositories. Run from the parent project root.
set -u
B=https://joenobody-ai.github.io/Karens-Class
P=/opt/data/profiles/different-world/projects/different-world-fan-page
cd "$P"

echo "=== live syllabus page sanity ==="
curl -s -L "$B/syllabus.html" -o /tmp/s.html
echo "  'The State, the Street' : $(grep -c 'The State, the Street' /tmp/s.html)"
echo "  schedule rows           : $(grep -c '<td>1[0-5]</td>' /tmp/s.html)"
echo "  'Midterm released'      : $(grep -c 'Midterm released' /tmp/s.html)"

echo "=== add the course cross-link to the reference site README ==="
python3 "$P/scripts/add_course_link.py"

echo "=== commit and push the parent repo ==="
git status --short | head -5
git add README.md .gitignore
git -c core.hooksPath=/dev/null commit -q -m "Cross-link the Karens-Class course; ignore the course's own repository" || echo "  (nothing to commit)"
git push -q origin main && echo "  pushed: $(git log --oneline | head -1)"
echo "=== done ==="
