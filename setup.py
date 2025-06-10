#!/usr/bin/env python3

import os
import subprocess
import shutil
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py


def find_ngspice_paths():
    """Find ngspice installation paths dynamically."""
    # Try to find ngspice executable
    ngspice_exe = shutil.which('ngspice')
    if not ngspice_exe:
        raise RuntimeError("ngspice executable not found in PATH. Please install ngspice.")
    
    # Get the base installation directory (usually bin/../ from executable)
    ngspice_exe_path = Path(ngspice_exe).resolve()
    base_dir = ngspice_exe_path.parent.parent  # bin/../
    
    # Try different common paths for include and lib directories
    possible_include_dirs = [
        base_dir / "include",
        base_dir / "include" / "ngspice",
        Path("/usr/include"),
        Path("/usr/local/include"),
        Path("/opt/homebrew/include"),  # macOS Homebrew
    ]
    
    possible_lib_dirs = [
        base_dir / "lib",
        base_dir / "lib64", 
        Path("/usr/lib"),
        Path("/usr/local/lib"),
        Path("/opt/homebrew/lib"),  # macOS Homebrew
    ]
    
    # Find include directory
    include_dir = None
    for inc_dir in possible_include_dirs:
        if inc_dir.exists() and (inc_dir / "ngspice").exists() or (inc_dir / "ngspice.h").exists():
            include_dir = str(inc_dir)
            break
    
    if not include_dir:
        # Fallback: check if any of the directories exist
        for inc_dir in possible_include_dirs:
            if inc_dir.exists():
                include_dir = str(inc_dir)
                break
    
    # Find lib directory with libngspice
    lib_dir = None
    for lib_d in possible_lib_dirs:
        if lib_d.exists():
            # Check for libngspice.so or libngspice.a
            if any(lib_d.glob("libngspice.*")):
                lib_dir = str(lib_d)
                break
    
    if not lib_dir:
        # Fallback: use first existing lib directory
        for lib_d in possible_lib_dirs:
            if lib_d.exists():
                lib_dir = str(lib_d)
                break
    
    if not include_dir:
        raise RuntimeError(f"ngspice include directory not found. Searched: {[str(p) for p in possible_include_dirs]}")
    if not lib_dir:
        raise RuntimeError(f"ngspice lib directory not found. Searched: {[str(p) for p in possible_lib_dirs]}")
    
    print(f"Found ngspice installation:")
    print(f"  Executable: {ngspice_exe}")
    print(f"  Include dir: {include_dir}")
    print(f"  Lib dir: {lib_dir}")
    
    return include_dir, lib_dir


class BuildVpiCommand(build_py):
    """Custom build command that builds the VPI module using g++."""

    def run(self):
        print("Building VPI module with g++...")
        
        # Ensure spicebind directory exists
        spicebind_dir = Path("spicebind")
        spicebind_dir.mkdir(exist_ok=True)
        
        # Find ngspice paths dynamically
        try:
            ngspice_include, ngspice_lib = find_ngspice_paths()
        except RuntimeError as e:
            print(f"Error finding ngspice: {e}")
            raise
        
        # Build command with dynamic paths
        build_cmd = [
            "g++",
            "-shared",
            "-fPIC", 
            "-std=c++17",
            "-I./cpp",
            f"-I{ngspice_include}",
            f"-L{ngspice_lib}",
            "-lngspice",
            "cpp/SpiceVpiConfig.cpp",
            "cpp/AnalogDigitalInterface.cpp", 
            "cpp/NgSpiceCallbacks.cpp",
            "cpp/VpiCallbacks.cpp",
            "cpp/vpi_module.cpp",
            "-o",
            "spicebind/spicebind_vpi.vpi"
        ]
        
        print(f"Running: {' '.join(build_cmd)}")
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Build failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            raise RuntimeError("VPI module build failed")
        
        print("Successfully built VPI module")
        
        # Run the standard build_py
        super().run()


setup(
    name="spicebind",
    version="0.0.1",
    author="Tomasz Hemperek",
    description="SpiceBind is a bridge that embeds the ngspice analog engine inside VPI-capable Verilog simulator for mixed-signal co-simulation.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={
        "spicebind": ["*.vpi"],
    },
    include_package_data=True,
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'spicebind-vpi-path=spicebind.cli:main',
        ],
    },
    cmdclass={
        'build_py': BuildVpiCommand,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 
