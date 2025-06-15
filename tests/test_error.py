import cocotb
from cocotb.triggers import Timer
from cocotb.runner import get_runner
import os
from pathlib import Path
import spicebind
import pytest

@cocotb.test()
async def run_error_test(dut):
    await Timer(10, units="ns")
    # assert False, "Error"

@pytest.mark.xfail(reason="Expected error from spice simulation")
def test_error():
    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "error.v"]

    sim = os.getenv("SIM", "icarus")

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="error_tb",
        always=True,
    )

    runner.test(
        hdl_toplevel="error_tb",
        test_module="test_error,",
        test_args=["-M", spicebind.get_lib_dir(), "-m", "spicebind_vpi"],
        extra_env={"SPICE_NETLIST": str(proj_path / "error.cir"), "HDL_INSTANCE": "error_tb.error_cir"},
    )


if __name__ == "__main__":
    test_error()
