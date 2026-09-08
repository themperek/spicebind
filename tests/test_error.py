import cocotb
from cocotb.triggers import Timer

from cocotb_tools.runner import get_runner

from pathlib import Path
import spicebind
import pytest


@cocotb.test()
async def run_error_test(dut):
    await Timer(10, unit="ns")
    # assert False, "Error"


@pytest.mark.xfail(reason="Expected error from spice simulation")
def test_error():
    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "error.v"]

    args = spicebind.cocotb_vpi_args()
    sim = args["sim"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="error_tb",
        always=True,
        build_args=args["build_args"],
        timescale=("1ns", "1ps"),
        waves=args["waves"],
        build_dir=str(proj_path / "sim_build" / sim),
    )

    runner.test(
        hdl_toplevel="error_tb",
        test_module="test_error,",
        test_args=args["test_args"],
        plusargs=args["plusargs"],
        extra_env={
            "SPICE_NETLIST": str(proj_path / "error.cir"),
            "HDL_INSTANCE": "error_tb.error_cir",
        },
    )


if __name__ == "__main__":
    test_error()
