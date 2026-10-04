.PHONY: help build build-v1 build-v2 verify verify-v1 verify-v2 check scenes import art photos clean all

help:
	@echo "A Different World — Origin Notes"
	@echo ""
	@echo "  make build      rebuild V1 (text) + V2 (Netflix-style) from data/"
	@echo "  make build-v1   rebuild index.html + ep01..ep10.html only"
	@echo "  make build-v2   rebuild v2/index.html + v2/ep01..ep10.html only"
	@echo "  make check      validate the data only (no writes)"
	@echo "  make verify     every machine check: 175 + 361 structural, 25 + 26 jsdom"
	@echo "  make art        redraw the generated SVG artwork (assets/art)"
	@echo "  make photos     re-download the credited Commons campus photos"
	@echo "  make images     check SVG validity + that hotlinked key art still returns 200"
	@echo "  make scenes     run the scene finder over every imported transcript"
	@echo "  make import     import subtitle files from subtitles/"
	@echo "  make all        build + verify"
	@echo "  make clean      remove generated pages (data/ and assets/ are never touched)"

build: build-v1 build-v2

build-v1:
	python3 scripts/build_pages.py

build-v2:
	python3 scripts/build_v2.py

check:
	python3 scripts/build_pages.py --check

verify: verify-v1 verify-v2

verify-v1:
	python3 scripts/verify_pages.py
	node scripts/verify_pages.mjs

verify-v2:
	python3 scripts/verify_v2.py
	node scripts/verify_v2.mjs

art:
	python3 scripts/make_art.py --force

photos:
	python3 scripts/fetch_commons.py

images:
	bash scripts/check_images.sh

import:
	python3 scripts/import_subtitles.py

scenes:
	python3 scripts/find_scenes.py --all --out data/candidates

coverage:
	python3 scripts/find_scenes.py --coverage

all: build verify
