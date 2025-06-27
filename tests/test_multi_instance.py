import cocotb
from cocotb.triggers import Timer
from cocotb.runner import get_runner
import os
from pathlib import Path
import spicebind
import pytest


@cocotb.test()
async def run_multi_instance(dut):
    dut.A0.value = 0
    dut.A1.value = 0

    await Timer(5, units="ns")
    assert dut.Y0.value == 1
    assert dut.Y1.value == 1

    # A0 -> 1
    await Timer(10, units="ns")
    dut.A0.value = 1

    await Timer(2, units="ns")
    assert dut.Y0.value == 1
    assert dut.Y1.value == 1

    await Timer(3, units="ns")
    assert dut.Y0.value == "x"
    assert dut.Y1.value == 1

    await Timer(5, units="ns")
    assert dut.Y0.value == 0
    assert dut.Y1.value == 1

    # A1 -> 1
    await Timer(10, units="ns")
    dut.A1.value = 1

    await Timer(10, units="ns")
    dut.A0.value = 0
    await Timer(10, units="ns")
    dut.A1.value = 0
    await Timer(10, units="ns")


def test_multi_instance():
    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "multi_instance.v"]

    sim = os.getenv("SIM", "icarus")

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="tb",
        always=True,
    )

    runner.test(
        hdl_toplevel="tb",
        test_module="test_multi_instance,",
        test_args=["-M", spicebind.get_lib_dir(), "-m", "spicebind_vpi"],
        extra_env={
            "SPICE_NETLIST": str(proj_path / "multi_instance.cir"),
            "HDL_INSTANCE": "tb.inv0,tb.inv1",
            "VCC": "1.8",
        },
    )


if __name__ == "__main__":
    test_multi_instance()
