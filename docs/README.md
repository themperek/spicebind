SpiceBind documentation
=======================

This directory contains the documentation of SpiceBind, which is built with Doxygen and Sphinx.
The documentation is automatically built and uploaded with every pull request.

`nox -e docs` can be used to create an appropriate virtual environment and
invoke `sphinx-build` to generate the HTML docs.

The OrConf 2026 slides are exported with [Marp CLI](https://github.com/marp-team/marp-cli)
during that build (`View slides` plus `SpiceBind-OrConf-2026.pdf`). Install `marp`
on your PATH, or the build copies a fallback PDF if `docs/talks/orconf-2026/slides.md`
was already exported locally. Do not add `slides.md` to the Sphinx toctree; the
YAML front matter is for Marp, not Myst.

In addition to the Python dependencies managed by `nox`, `doxygen` must be
installed.

Other nox environments (run with `nox -e <env>`):
* `docs_linkcheck` - run the Sphinx `linkcheck` builder
* `docs_spelling` - run a spellchecker on the documentation
