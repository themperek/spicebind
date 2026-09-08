import cocotb
from cocotb.triggers import Timer

from cocotb_tools.runner import get_runner

from pathlib import Path
import spicebind
from rawread import rawread


def check_transition(time, vals, trans_time, start, stop):
    edges = [
        i
        for i in range(len(vals) - 1)
        if abs(vals[i] - start) <= 0.01 and abs(vals[i + 1] - stop) <= 0.01
    ]
    if not edges:
        assert False, f"No {start} -> {stop} transition in waveform"
    i = min(edges, key=lambda k: abs(float(time[k + 1]) - trans_time))
    if abs(float(time[i + 1]) - trans_time) > 1.0e-9:
        assert False, (
            f"Nearest {start} -> {stop} edge at {float(time[i + 1])}, expected {trans_time}"
        )


@cocotb.test()
async def run_debug(dut):
    dut.A2.value = 0
    dut.A1.value = 0
    dut.A0.value = 0
    await Timer(0.1, unit="ns")

    assert dut.Y0.value == 0
    assert dut.Y1.value == 0
    assert dut.Y2.value == 0
    await Timer(2, unit="ns")

    dut.A2.value = 1
    await Timer(0.1, unit="ns")
    dut.A0.value = 1
    await Timer(0.1, unit="ns")
    assert dut.Y0.value == 1

    dut.A1.value = 1
    await Timer(0.1, unit="ns")
    await Timer(2, unit="ns")
    dut.A2.value = 0
    await Timer(0.1, unit="ns")

    assert dut.Y1.value == 1
    assert dut.Y2.value == 1

    dut.A0.value = 0
    await Timer(0.1, unit="ns")
    assert dut.Y0.value == 0

    await Timer(1, unit="ns")
    assert dut.Y2.value == 0

    dut.A1.value = 0
    await Timer(0.1, unit="ns")


def test_debug():
    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "debug.v"]
    args = spicebind.cocotb_vpi_args(debug=True)
    sim = args["sim"]
    build_dir = proj_path / "sim_build" / sim

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="tb",
        always=True,
        build_args=args["build_args"],
        timescale=("1ns", "1ps"),
        waves=args["waves"],
        build_dir=str(build_dir),
    )

    runner.test(
        hdl_toplevel="tb",
        test_module="test_debug,",
        test_args=args["test_args"],
        plusargs=args["plusargs"],
        extra_env={
            "SPICE_NETLIST": str(proj_path / "debug.cir"),
            "HDL_INSTANCE": "tb.debug",
            "VCC": "1.8",
            "SPICE_DUMP_RAW": "1",
        },
    )

    arrs, plots = rawread(str(build_dir / "dump.raw"))

    check_transition(arrs[0]["time"], arrs[0]["v(a0)"], 2.2e-09, 0.0, 1.8)
    check_transition(arrs[0]["time"], arrs[0]["v(a0)"], 4.5e-09, 1.8, 0.0)

    check_transition(arrs[0]["time"], arrs[0]["v(a2)"], 2.1e-09, 0.0, 1.8)
    check_transition(arrs[0]["time"], arrs[0]["v(a2)"], 4.4e-09, 1.8, 0.0)

    check_transition(arrs[0]["time"], arrs[0]["v(a1)"], 2.3e-09, 0.0, 1.8)
    check_transition(arrs[0]["time"], arrs[0]["v(a1)"], 5.6e-09, 1.8, 0.0)


if __name__ == "__main__":
    test_debug()
