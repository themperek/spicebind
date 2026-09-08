# Build the OrConf 2026 deck. Run from this directory.
#
#   make pdf     # SpiceBind-OrConf-2026.pdf
#   make html    # index.html (browser deck)
#   make preview # live reload
#
# Needs Marp CLI: npm install -g @marp-team/marp-cli

MARP ?= marp
TALK := slides.md
PDF  := SpiceBind-OrConf-2026.pdf
HTML := index.html

.PHONY: all html pdf preview

all: html pdf

html: $(HTML)

pdf: $(PDF)

$(HTML): $(TALK)
	$(MARP) --html --allow-local-files $(TALK) -o $(HTML)

$(PDF): $(TALK)
	$(MARP) --pdf --allow-local-files $(TALK) -o $(PDF)

preview:
	$(MARP) --preview --allow-local-files $(TALK)
