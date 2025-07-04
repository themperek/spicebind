SpiceBind documentation
=======================

This directory contains the documentation of SpiceBind, which is built with Doxygen and Sphinx.
The documentation is automatically built and uploaded with every pull request.

`nox -e docs` can be used to create an appropriate virtual environment and
invoke `sphinx-build` to generate the HTML docs.

In addition to the Python dependencies managed by `nox`, `doxygen` must be
installed.

Other nox environments (run with `nox -e <env>`):
* `docs_linkcheck` - run the Sphinx `linkcheck` builder
* `docs_spelling` - run a spellchecker on the documentation
