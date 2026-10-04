#!/usr/bin/env python3
"""add_course_link.py — append a cross-link to the Karens-Class course into the reference site's README.

Idempotent: does nothing if the link is already there.
"""
from __future__ import annotations

import pathlib

README = pathlib.Path(__file__).resolve().parents[1] / "README.md"

BLOCK = """
## Related: the course built on this site

**[Karens-Class](https://github.com/joeNobody-ai/Karens-Class)** — a 15-session upper-division sociology
seminar, *A Different World*: Black Experience and American Society, taught from this site's documented
callback pairs. Each session pairs a 2026 episode with its 1987–1993 counterpart; the homework assigns
this site's callback cards as evidence to be checked. Syllabus, 15 assignments, midterm, final, rubrics
and instructor keys all included.

- Repository: https://github.com/joeNobody-ai/Karens-Class
- Course site: https://joenobody-ai.github.io/Karens-Class/
"""


def main() -> int:
    text = README.read_text()
    if "Karens-Class" in text:
        print("  cross-link already present — nothing to do")
        return 0
    README.write_text(text.rstrip() + "\n" + BLOCK)
    print("  appended the course cross-link to README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
