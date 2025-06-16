#!/usr/bin/env python3
"""
Command line interface for spicebind.
"""


def get_lib_dir():
    """Get the path to the VPI module."""
    from pathlib import Path

    # Check in package directory (same directory as this file)
    package_dir = Path(__file__).parent
    vpi_path = package_dir / "spicebind_vpi.vpi"
    if vpi_path.exists():
        return str(vpi_path.parent)

    # Check in current directory
    local_vpi = Path("spicebind_vpi.vpi")
    if local_vpi.exists():
        return str(local_vpi.parent)

    return None


def main():
    """Main entry point for spicebind-vpi-path command."""
    import sys

    vpi_path = get_lib_dir()
    if vpi_path:
        print(vpi_path)
        sys.exit(0)
    else:
        print("Error: spicebind library not found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
