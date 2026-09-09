"""Analog between the logic thresholds must drive HDL X (Icarus 4-state)."""

from __future__ import annotations

import os
from pathlib import Path

import cocotb
import spicebind
from cocotb.triggers import ReadWrite, Timer
from cocotb_tools.runner import get_runner

VCC = 1.0
# Defaults in Config.cpp: 0.3*VCC / 0.7*VCC. Equal to a bound is still X.
LOW = 0.3 * VCC
HIGH = 0.7 * VCC


def _bit(sig) -> str:
    text = str(sig.value).lower()
    if text in ("x", "z"):
        return text
    return str(int(sig.value))


async def _drive(dut, volts: float) -> str:
    dut.vin.value = volts
    await Timer(20, unit="ns")
    await ReadWrite()
    return _bit(dut.y)


@cocotb.test()
async def analog_midband_is_x(dut):
    sim = os.getenv("SIM", "icarus")

    assert await _drive(dut, 0.0) == "0"
    assert await _drive(dut, LOW - 0.05) == "0"
    assert await _drive(dut, HIGH + 0.05) == "1"
    assert await _drive(dut, VCC) == "1"

    for volts in (LOW, 0.5 * VCC, HIGH):
        got = await _drive(dut, volts)
        if sim == "verilator":
            assert got in ("0", "1"), f"vin={volts} Verilator y={got}"
        else:
            assert got == "x", f"vin={volts} VCC={VCC} expected X got {got}"


def test_logic_x():
    proj_path = Path(__file__).resolve().parent
    args = spicebind.cocotb_vpi_args()
    sim = args["sim"]
    build_dir = (proj_path / "sim_build" / f"{sim}_logic_x").resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    cir_path = build_dir / "test.cir"
    cir_path.write_text((proj_path / "logic_x.cir").read_text().format(VCC=VCC))

    runner = get_runner(sim)
    runner.build(
        sources=[proj_path / "tb_logic_x.v"],
        hdl_toplevel="tb",
        always=True,
        build_dir=build_dir,
        build_args=args["build_args"],
        timescale=("1ns", "1ps"),
        waves=args["waves"],
    )
    runner.test(
        hdl_toplevel="tb",
        test_module="test_logic_x,",
        test_args=args["test_args"],
        plusargs=args["plusargs"],
        extra_env={
            "SPICE_NETLIST": str(cir_path),
            "HDL_INSTANCE": "tb.test_cir",
            "VCC": str(VCC),
        },
    )
