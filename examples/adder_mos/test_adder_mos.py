"""Four-bit CMOS adder: empty HDL module implemented by ngspice."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import spicebind

EXAMPLE = Path(__file__).resolve().parent


def test_adder_mos():
    sim = os.getenv("SIM", "icarus")
    env = os.environ.copy()
    env.update(
        {
            "SPICE_NETLIST": str(EXAMPLE / "adder_mos.cir"),
            "HDL_INSTANCE": "adder_tb.dut",
            "VCC": "3.3",
        }
    )
    build_dir = EXAMPLE / "sim_build" / sim
    build_dir.mkdir(parents=True, exist_ok=True)

    if sim == "verilator":
        vpi = spicebind.get_vpi_module_path()
        if not vpi:
            raise RuntimeError("spicebind_vpi.vpi not found")
        obj_dir = build_dir / "obj_dir"
        compile_result = subprocess.run(
            [
                "verilator",
                "--binary",
                "-j",
                "0",
                "--vpi",
                "--timing",
                "--public-flat-rw",
                "--fno-inline",
                "--trace",
                "--timescale",
                "1ns/1ns",
                "--top-module",
                "adder_tb",
                "--Wno-UNDRIVEN",
                "--Wno-UNUSED",
                "--Wno-UNOPTFLAT",
                "--Wno-WIDTHTRUNC",
                "--Mdir",
                str(obj_dir),
                "-o",
                "Vadder_tb",
                str(EXAMPLE / "tb.v"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                f"verilator failed:\n{compile_result.stdout}\n{compile_result.stderr}"
            )
        cmd = [str(obj_dir / "Vadder_tb"), f"+verilator+vpi+{vpi}"]
    else:
        vvp_path = build_dir / "tb.vvp"
        compile_result = subprocess.run(
            ["iverilog", "-o", str(vvp_path), str(EXAMPLE / "tb.v")],
            capture_output=True,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                f"iverilog failed:\n{compile_result.stdout}\n{compile_result.stderr}"
            )
        cmd = [
            "vvp",
            "-M",
            spicebind.get_lib_dir(),
            "-m",
            "spicebind_vpi",
            str(vvp_path),
        ]

    result = subprocess.run(
        cmd,
        cwd=EXAMPLE,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or "Adder OK" not in result.stdout:
        raise AssertionError(
            f"{sim} adder_mos failed (exit {result.returncode}):\n"
            f"{result.stdout}\n{result.stderr}"
        )
