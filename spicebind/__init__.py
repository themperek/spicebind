"""
spicebind - Mixed-signal simulation for RTL simulators.

A Python package for integrating ngspice simulation into Verilog simulators
using the VPI interface.
"""

try:
    from importlib.metadata import version
    __version__ = version("spicebind")
except ImportError:
    # Fallback for Python < 3.8 (though you require 3.8+)
    from importlib_metadata import version
    __version__ = version("spicebind")
except Exception:
    # Fallback for development environments where package isn't installed
    __version__ = "dev"


def get_package_path():
    """Get the path to the installed spicebind package directory."""
    from pathlib import Path

    return str(Path(__file__).parent)


def get_lib_dir():
    """Get the directory to the spicebind library."""
    import os

    return os.path.dirname(get_vpi_module_path())


def get_vpi_module_path():
    """Get the path to the VPI module."""
    from pathlib import Path

    # Check in package directory
    package_dir = Path(__file__).parent
    vpi_path = package_dir / "spicebind_vpi.vpi"
    if vpi_path.exists():
        return str(vpi_path)

    # Check in current directory
    local_vpi = Path("spicebind_vpi.vpi")
    if local_vpi.exists():
        return str(local_vpi)

    return None


def print_installation_info():
    """Print information about the spicebind installation."""
    print(f"spicebind v{__version__}")
    print(f"Package location: {get_package_path()}")
    vpi_path = get_vpi_module_path()
    if vpi_path:
        print(f"VPI module location: {vpi_path}")
    else:
        print("VPI module not found")
