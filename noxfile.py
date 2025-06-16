# PEP723; see https://nox.thea.codes/en/stable/tutorial.html#running-without-the-nox-command-or-adding-dependencies
# /// script
# dependencies = [
#   "nox>=2025.5.1",
# ]
# ///

"""Setup file for nox (https://nox.thea.codes/en/stable/tutorial.html)."""

from functools import cache

import nox

import tomllib  # Python 3.11+; use `tomli` for earlier versions


@cache
def get_doc_dependencies():
    with open("pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject["project"]["optional-dependencies"]["docs"]


@nox.session
def docs(session: nox.Session) -> None:
    """Invoke sphinx-build to build the HTML docs."""
    doc_deps = get_doc_dependencies()
    session.install(*doc_deps)
    outdir = session.cache_dir / "docs_out"
    session.run(
        "sphinx-build",
        "./docs/source",
        str(outdir),
        "--color",
        "-b",
        "html",
        *session.posargs,
    )
    index = (outdir / "index.html").resolve().as_uri()
    session.log(f"Documentation is available at {index}")


@nox.session
def docs_preview(session: nox.Session) -> None:
    """Build a live preview of the documentation."""
    doc_deps = get_doc_dependencies()
    session.install(*doc_deps)
    # Editable install allows editing source and seeing it updated in the live preview
    # session.run("pip", "install", ".[docs]")
    outdir = session.cache_dir / "docs_out"
    # fmt: off
    session.run(
        "sphinx-autobuild",
        # Ignore directories which cause a rebuild loop.
        "--ignore", "*/doxygen/*",
        # Ignore nox's venv directory.
        "--ignore", ".nox",
        # Ignore emacs backup files.
        "--ignore", "**/#*#",
        "--ignore", "**/.#*",
        # Ignore vi backup files.
        "--ignore", "**/.*.sw[px]",
        "--ignore", "**/*~",
        # FIXME: local to cmarqu :)
        "--ignore", "*@*:*",
        "./docs/source",
        str(outdir),
        *session.posargs,
    )
    # fmt: on


@nox.session
def docs_linkcheck(session: nox.Session) -> None:
    """Invoke sphinx-build to linkcheck the docs."""
    doc_deps = get_doc_dependencies()
    session.install(*doc_deps)
    outdir = session.cache_dir / "docs_out"
    session.run(
        "sphinx-build",
        "./docs/source",
        str(outdir),
        "--color",
        "-b",
        "linkcheck",
        *session.posargs,
    )


@nox.session
def docs_spelling(session: nox.Session) -> None:
    """Invoke sphinx-build to spellcheck the docs."""
    doc_deps = get_doc_dependencies()
    session.install(*doc_deps)
    outdir = session.cache_dir / "docs_out"
    session.run(
        "sphinx-build",
        "./docs/source",
        str(outdir),
        "--color",
        "-b",
        "spelling",
        *session.posargs,
    )
