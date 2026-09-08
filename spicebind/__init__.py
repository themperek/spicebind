"""
spicebind - Mixed-signal simulation for RTL simulators.

A Python package for integrating ngspice simulation into Verilog simulators
using the VPI interface.
"""

try:
    from importlib.metadata import version
    __version__ = version("spicebind")
except Exception:
    # Fallback for development environments where package isn't installed
    __version__ = "dev"


def get_package_path():
    """Get the path to the installed spicebind package directory."""
    from pathlib import Path

    return str(Path(__file__).parent)


def _vpi_filename(debug=False):
    return "spicebind_vpi_debug.vpi" if debug else "spicebind_vpi.vpi"


def get_lib_dir():
    """Get the directory to the spicebind library."""
    import os

    path = get_vpi_module_path() or get_vpi_module_path(debug=True)
    if not path:
        return None
    return os.path.dirname(path)


def get_vpi_module_path(debug=False):
    """Get the path to the VPI module (release, or debug if debug=True)."""
    from pathlib import Path

    filename = _vpi_filename(debug)
    package_dir = Path(__file__).parent
    vpi_path = package_dir / filename
    if vpi_path.exists():
        return str(vpi_path)

    local_vpi = Path(filename)
    if local_vpi.exists():
        return str(local_vpi)

    return None


# Shared with cocotb examples/tests. Cocotb already passes --vpi --public-flat-rw.
VERILATOR_BUILD_ARGS = (
    "--timing",
    "--fno-inline",
    "--trace",
    "--Wno-UNDRIVEN",
    "--Wno-UNUSED",
)


def cocotb_vpi_args(sim=None, *, debug=False, extra_build_args=None, vpi=True):
    """Icarus/Verilator args for cocotb ``runner.build`` / ``runner.test``.

    ``sim`` defaults to ``$SIM`` or ``icarus``. Set ``vpi=False`` for HDL-only
    benches that still need Verilator ``--timing``. ``extra_build_args`` are
    appended only for Verilator. Verilator sets ``waves`` so ``$dumpvars`` can
    run (cocotb must compile with ``VM_TRACE=1``).
    """
    import os

    sim = sim or os.getenv("SIM", "icarus")
    extra_build_args = list(extra_build_args or [])
    build_args = []
    test_args = []
    plusargs = []

    if sim == "verilator":
        build_args = list(VERILATOR_BUILD_ARGS) + extra_build_args
        if vpi:
            vpi_path = get_vpi_module_path(debug=debug)
            if not vpi_path:
                raise RuntimeError(f"{_vpi_filename(debug)} not found")
            plusargs = [f"+verilator+vpi+{vpi_path}"]
    elif vpi:
        lib_dir = get_lib_dir()
        if not lib_dir:
            raise RuntimeError(f"{_vpi_filename(debug)} not found")
        module = "spicebind_vpi_debug" if debug else "spicebind_vpi"
        test_args = ["-M", lib_dir, "-m", module]

    return {
        "sim": sim,
        "build_args": build_args,
        "test_args": test_args,
        "plusargs": plusargs,
        # Cocotb must compile with VM_TRACE=1 so $dumpvars can call traceEverOn.
        "waves": sim == "verilator",
    }


def print_installation_info():
    """Print information about the spicebind installation."""
    print(f"spicebind v{__version__}")
    print(f"Package location: {get_package_path()}")
    vpi_path = get_vpi_module_path()
    if vpi_path:
        print(f"VPI module location: {vpi_path}")
    else:
        print("VPI module not found")
