# PEP723; see https://nox.thea.codes/en/stable/tutorial.html#running-without-the-nox-command-or-adding-dependencies
# /// script
# dependencies = [
#   "nox>=2025.5.1",
# ]
# ///

"""Setup file for nox (https://nox.thea.codes/en/stable/tutorial.html)."""


import nox

# Python 3.11+ has tomllib built-in, use tomli for earlier versions
try:
    import tomllib
except ImportError:
    import tomli as tomllib


def get_doc_dependencies():
    with open("pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject["project"]["optional-dependencies"]["docs"]


def get_dev_dependencies():
    with open("pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject["project"]["optional-dependencies"]["dev"]


@nox.session
def test(session: nox.Session) -> None:
    """Run the test suite with pytest."""
    dev_deps = get_dev_dependencies()
    session.install(".", *dev_deps)
    session.run("pytest", *session.posargs)


@nox.session
def test_sdist(session: nox.Session) -> None:
    """Test that the package works after creating and installing from sdist."""
    # Install build tool
    session.install("build")
    
    # Create source distribution
    session.run("python", "-m", "build", "--sdist", "--outdir", session.cache_dir)
    
    # Find the created sdist file
    import glob
    sdist_files = glob.glob(str(session.cache_dir / "*.tar.gz"))
    if not sdist_files:
        session.error("No sdist file found")
    
    # Install from sdist along with dev dependencies
    dev_deps = get_dev_dependencies()
    session.install(sdist_files[0], *dev_deps)
    
    # Run tests to ensure everything works
    session.run("pytest", *session.posargs)


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
