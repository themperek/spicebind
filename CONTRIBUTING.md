# Contributing

Thanks for helping with SpiceBind.

## Setup

You need a C++17 compiler, ngspice (library and headers), a VPI-capable Verilog simulator (Icarus Verilog is what CI uses), and Python 3.10+.

```bash
pip install -e ".[dev]"
```

Standalone VPI build (no Python package):

```bash
cmake -S . -B build
cmake --build build
```

Rebuild the VPI after C++ changes.

## Tests

```bash
nox -s test
```

CI runs that session on Python 3.10 and 3.13 with Icarus Verilog and ngspice.

## Pull requests

- Open an issue first for larger changes.
- Keep the diff focused, and add or update tests when behavior changes.
- Do not bump the package version or publish to PyPI unless a maintainer asks.
