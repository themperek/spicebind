import os
from pathlib import Path

import cocotb
import spicebind
from cocotb.triggers import Timer
from cocotb_tools.runner import get_runner


@cocotb.test()
async def run_multi_instance(dut):
    dut.A0.value = 0
    dut.A1.value = 0

    await Timer(5, unit="ns")
    assert dut.Y0.value == 1
    assert dut.Y1.value == 1

    # A0 -> 1
    await Timer(10, unit="ns")
    dut.A0.value = 1

    await Timer(2, unit="ns")
    assert dut.Y0.value == 1
    assert dut.Y1.value == 1

    await Timer(3, unit="ns")
    # Verilator stores 2-state bits, so analog-mid (vpiX) collapses to 0/1.
    if os.getenv("SIM", "icarus") == "verilator":
        assert dut.Y0.value in (0, 1, "x")
    else:
        assert dut.Y0.value == "x"
    assert dut.Y1.value == 1

    await Timer(5, unit="ns")
    assert dut.Y0.value == 0
    assert dut.Y1.value == 1

    # A1 -> 1
    await Timer(10, unit="ns")
    dut.A1.value = 1

    await Timer(10, unit="ns")
    dut.A0.value = 0
    await Timer(10, unit="ns")
    dut.A1.value = 0
    await Timer(10, unit="ns")


def test_multi_instance():
    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "multi_instance.v"]
    args = spicebind.cocotb_vpi_args()
    sim = args["sim"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="tb",
        always=True,
        build_args=args["build_args"],
        timescale=("1ns", "1ps"),
        waves=args["waves"],
        build_dir=str(proj_path / "sim_build" / sim),
    )

    runner.test(
        hdl_toplevel="tb",
        test_module="test_multi_instance,",
        test_args=args["test_args"],
        plusargs=args["plusargs"],
        extra_env={
            "SPICE_NETLIST": str(proj_path / "multi_instance.cir"),
            "HDL_INSTANCE": "tb.inv0,tb.inv1",
            "VCC": "1.8",
        },
    )


if __name__ == "__main__":
    test_multi_instance()
