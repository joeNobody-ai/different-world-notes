.PHONY: help build verify check scenes import clean all

help:
	@echo "A Different World — Origin Notes"
	@echo ""
	@echo "  make build    rebuild index.html + ep01..ep10.html from data/"
	@echo "  make check    validate the data only (no writes)"
	@echo "  make verify   the machine checks (structural + jsdom behaviour)"
	@echo "  make scenes   run the scene finder over every imported transcript"
	@echo "  make import   import subtitle files from subtitles/"
	@echo "  make all      build + verify"
	@echo "  make clean    remove generated pages (data/ is never touched)"

build:
	python3 scripts/build_pages.py

check:
	python3 scripts/build_pages.py --check

verify:
	python3 scripts/verify_pages.py
	node scripts/verify_pages.mjs

all: build verify

import:
	python3 scripts/import_subtitles.py

scenes:
	python3 scripts/find_scenes.py --all --out data/candidates

coverage:
	python3 scripts/find_scenes.py --coverage

clean:
	rm -f index.html ep01.html ep02.html ep03.html ep04.html ep05.html \
	      ep06.html ep07.html ep08.html ep09.html ep10.html
