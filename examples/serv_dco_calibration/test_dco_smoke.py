"""Autonomous SPICE ring oscillator -> HDL edges through SpiceBind."""

from __future__ import annotations

import os
from pathlib import Path

import cocotb
from cocotb.triggers import RisingEdge, Timer, ReadWrite, with_timeout
from cocotb_tools.runner import get_runner
import spicebind

from corners import CORNERS, render_netlist

EXAMPLE = Path(__file__).resolve().parent


@cocotb.test()
async def run_oscillator_enable_and_edges(dut):
    dut.enable.value = 0
    dut.trim.value = 7
    await Timer(200, unit="ns")
    await ReadWrite()

    stuck = int(dut.osc.value)
    for _ in range(20):
        await Timer(20, unit="ns")
        await ReadWrite()
        assert int(dut.osc.value) == stuck, "oscillator toggled while enable=0"

    dut.enable.value = 1
    await Timer(50, unit="ns")
    await ReadWrite()

    edges = 0

    async def count_edges(n):
        nonlocal edges
        for _ in range(n):
            await RisingEdge(dut.osc)
            edges += 1

    await with_timeout(count_edges(8), 2000, "ns")
    assert edges == 8, f"expected 8 rising edges, got {edges}"


def test_dco_smoke():
    corner = CORNERS["nominal"]
    args = spicebind.cocotb_vpi_args()
    sim = args["sim"]
    build_dir = (EXAMPLE / "sim_build" / sim / "dco_smoke").resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    cir_path = build_dir / "dco.cir"
    render_netlist(cir_path, corner, tran_step="0.1ns", tran_stop="20us")

    runner = get_runner(sim)
    runner.build(
        sources=[EXAMPLE / "rtl" / "tb_dco_smoke.v", EXAMPLE / "rtl" / "dco_core.v"],
        hdl_toplevel="tb_dco_smoke",
        always=True,
        build_dir=build_dir,
        build_args=args["build_args"],
        timescale=("1ns", "1ps"),
        waves=args["waves"],
    )
    runner.test(
        hdl_toplevel="tb_dco_smoke",
        test_module="test_dco_smoke",
        test_args=args["test_args"],
        plusargs=args["plusargs"],
        extra_env={
            "SPICE_NETLIST": str(cir_path),
            "HDL_INSTANCE": "tb_dco_smoke.dco",
            "VCC": str(corner["vdd"]),
        },
        build_dir=build_dir,
    )


if __name__ == "__main__":
    test_dco_smoke()
