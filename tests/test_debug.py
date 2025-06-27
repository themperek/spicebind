import cocotb
from cocotb.triggers import Timer
from cocotb.runner import get_runner
import os
from pathlib import Path
import spicebind
import numpy as np
from rawread import rawread


def check_transition(time, vals, trans_time, start, stop):
    closest_index = np.argmin(np.abs(time - trans_time))
    if abs(vals[closest_index] - start) > 0.01:
        assert False, f"Start value is not correct: {vals[closest_index]} != {start}"
    if abs(vals[closest_index + 1] - stop) > 0.01:
        assert False, f"Stop value is not correct: {vals[closest_index+1]} != {stop}"


@cocotb.test()
async def run_debug(dut):
    dut.A2.value = 0
    dut.A1.value = 0
    dut.A0.value = 0
    await Timer(0.1, units="ns")

    assert dut.Y0.value == 0
    assert dut.Y1.value == 0
    assert dut.Y2.value == 0
    await Timer(2, units="ns")

    dut.A2.value = 1
    await Timer(0.1, units="ns")
    dut.A0.value = 1
    await Timer(0.1, units="ns")
    assert dut.Y0.value == 1

    dut.A1.value = 1
    await Timer(0.1, units="ns")
    await Timer(2, units="ns")
    dut.A2.value = 0
    await Timer(0.1, units="ns")

    assert dut.Y1.value == 1
    assert dut.Y2.value == 1

    dut.A0.value = 0
    await Timer(0.1, units="ns")
    assert dut.Y0.value == 0

    await Timer(1, units="ns")
    assert dut.Y2.value == 0

    dut.A1.value = 0
    await Timer(0.1, units="ns")


def test_debug():
    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "debug.v"]

    sim = os.getenv("SIM", "icarus")

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="tb",
        always=True,
    )

    runner.test(
        hdl_toplevel="tb",
        test_module="test_debug,",
        test_args=["-M", spicebind.get_lib_dir(), "-m", "spicebind_vpi_debug"],
        extra_env={
            "SPICE_NETLIST": str(proj_path / "debug.cir"),
            "HDL_INSTANCE": "tb.debug",
            "VCC": "1.8",
        },
    )

    arrs, plots = rawread("sim_build/dump.raw")

    check_transition(arrs[0]["time"], arrs[0]["v(a0)"], 2.2e-09, 0.0, 1.8)
    check_transition(arrs[0]["time"], arrs[0]["v(a0)"], 4.5e-09, 1.8, 0.0)

    check_transition(arrs[0]["time"], arrs[0]["v(a2)"], 2.1e-09, 0.0, 1.8)
    check_transition(arrs[0]["time"], arrs[0]["v(a2)"], 4.4e-09, 1.8, 0.0)

    check_transition(arrs[0]["time"], arrs[0]["v(a1)"], 2.3e-09, 0.0, 1.8)
    check_transition(arrs[0]["time"], arrs[0]["v(a1)"], 5.6e-09, 1.8, 0.0)


if __name__ == "__main__":
    test_debug()
