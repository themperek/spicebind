"""SERV firmware calibrates a DCO. Trim codes are chosen by firmware, not by cocotb."""

from __future__ import annotations

import csv
import json
import os
import shutil
import time
from pathlib import Path

import cocotb
import pytest
import spicebind
from cocotb.clock import Clock
from cocotb.triggers import ReadWrite, RisingEdge, Timer, with_timeout
from cocotb_tools.runner import get_runner

from corners import CORNERS, render_netlist

EXAMPLE = Path(__file__).resolve().parent
GENERATED = EXAMPLE / "generated"
RESULTS = EXAMPLE / "results"

# Must match fw/calibrate.c
TARGET = 32
TOL = 6
# Fast sim clock; WINDOW is scaled so the analog measure window stays ~400 ns.
CLK_NS = 5
WARMUP = 20
WINDOW = 80
SETTLE = 8
TIMEOUT_NS = 2_000_000


def _int(signal, default=0):
    try:
        return int(signal.value)
    except (ValueError, TypeError):
        return default


@cocotb.test()
async def run_firmware_calibrates(dut):
    expected_pass = os.environ.get("EXPECTED_PASS", "1") == "1"
    corner = os.environ.get("CORNER_NAME", "unknown")
    vdd = os.environ.get("CORNER_VDD", "")
    temp = os.environ.get("CORNER_TEMP", "")
    label = os.environ.get("CORNER_LABEL", corner)
    clk_ns = int(os.environ.get("CLK_NS", str(CLK_NS)))

    samples = []

    async def watch_measurements():
        while True:
            await RisingEdge(dut.u_periph.u_meas.done)
            await ReadWrite()
            trim = _int(dut.u_periph.trim)
            count = _int(dut.u_periph.u_meas.count)
            samples.append({"trim": trim, "count": count})
            dut._log.info(f"trim {trim:2d} -> count {count}")

    cocotb.start_soon(Clock(dut.clk, clk_ns, unit="ns").start())
    dut.rst.value = 1
    await Timer(10 * clk_ns, unit="ns")
    await ReadWrite()
    cocotb.start_soon(watch_measurements())
    dut.rst.value = 0

    async def wait_finished():
        while True:
            await RisingEdge(dut.clk)
            await ReadWrite()
            result = _int(dut.u_periph.fw_result, default=0)
            if result & 1:
                return result

    result = await with_timeout(wait_finished(), TIMEOUT_NS, "ns")
    await ReadWrite()

    fw_pass = bool(result & 2)
    exhausted = bool(result & 4)
    final_trim = (result >> 8) & 0xF
    final_count = _int(dut.u_periph.fw_final_count)
    iterations = _int(dut.u_periph.fw_iterations)
    enable = _int(dut.u_periph.o_enable)

    lines = [
        "",
        "SERV DCO calibration",
        "--------------------",
        f"corner: {corner}",
        f"label: {label}",
        f"VDD: {vdd}",
        f"temperature: {temp}",
        "",
    ]
    for sample in samples:
        lines.append(f"trim {sample['trim']:2d} -> count {sample['count']}")
    lines += [
        "",
        f"final trim: {final_trim}",
        f"final count: {final_count}",
        f"target: {TARGET}",
        f"iterations: {iterations}",
        f"range exhausted: {exhausted}",
        "PASS" if fw_pass else "FAIL",
        "",
    ]
    report = "\n".join(lines)
    dut._log.info(report)
    print(report, flush=True)

    assert enable == 0, "DCO should be disabled after the last measurement"
    assert iterations >= 1
    assert samples, "firmware never ran a measurement"
    assert samples[-1]["trim"] == final_trim
    if expected_pass:
        assert fw_pass, f"firmware reported FAIL, count={final_count} trim={final_trim}"
        assert abs(final_count - TARGET) <= TOL
    else:
        assert not fw_pass, "extreme condition should fail calibration"
        assert exhausted or abs(final_count - TARGET) > TOL

    Path("fw_result.json").write_text(
        json.dumps(
            {
                "corner": corner,
                "vdd": vdd,
                "temperature": temp,
                "samples": samples,
                "final_trim": final_trim,
                "final_count": final_count,
                "iterations": iterations,
                "fw_pass": fw_pass,
                "range_exhausted": exhausted,
                "expected_pass": expected_pass,
                "target_count": TARGET,
            },
            indent=2,
        )
        + "\n"
    )


def _local_sources(dco_rtl: Path) -> list[Path]:
    return [
        GENERATED / "serv_rtl.v",
        EXAMPLE / "rtl" / "simple_ram.v",
        EXAMPLE / "rtl" / "dco_measure.v",
        EXAMPLE / "rtl" / "dco_peripheral.v",
        dco_rtl,
        EXAMPLE / "rtl" / "top.v",
    ]


def _append_csv(row: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "serv_dco.csv"
    fieldnames = [
        "case",
        "vdd",
        "temperature",
        "initial_trim",
        "initial_count",
        "final_trim",
        "final_count",
        "target_count",
        "iterations",
        "fw_pass",
        "expected_pass",
        "wall_time_s",
    ]
    new_file = not path.exists()
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def _run(build_dir: Path, sources: list[Path], extra_env: dict, plusargs=None, test_args=None) -> dict:
    build_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GENERATED / "firmware.hex", build_dir / "firmware.hex")

    runner = get_runner(os.getenv("SIM", "icarus"))
    runner.build(
        sources=sources,
        hdl_toplevel="top",
        always=True,
        build_dir=build_dir,
        defines={"SERV_CLEAR_RAM": 1},
        parameters={"WARMUP": WARMUP, "WINDOW": WINDOW, "SETTLE": SETTLE},
        timescale=("1ns", "1ps"),
    )
    env = {
        "COCOTB_RESOLVE_X": "ZEROS",
        "CLK_NS": str(CLK_NS),
        **extra_env,
    }
    runner.test(
        hdl_toplevel="top",
        test_module="test_serv_dco",
        test_args=test_args or [],
        plusargs=plusargs or [],
        extra_env=env,
        build_dir=build_dir,
    )
    return json.loads((build_dir / "fw_result.json").read_text())


def test_serv_dco_behavioral():
    """Bring-up path: same firmware and MMIO, monotonic behavioral DCO."""
    assert (GENERATED / "firmware.hex").exists(), "generated/firmware.hex is missing"
    t0 = time.perf_counter()
    result = _run(
        build_dir=(EXAMPLE / "sim_build" / "serv_beh").resolve(),
        sources=_local_sources(EXAMPLE / "rtl" / "dco_core_beh.v"),
        extra_env={
            "CORNER_NAME": "behavioral",
            "CORNER_LABEL": "behavioral DCO",
            "CORNER_VDD": "n/a",
            "CORNER_TEMP": "n/a",
            "EXPECTED_PASS": "1",
        },
        plusargs=["+DCO_BEH_SCALE=1"],
    )
    wall = time.perf_counter() - t0
    assert result["fw_pass"]
    _append_csv(
        {
            "case": "behavioral",
            "vdd": "",
            "temperature": "",
            "initial_trim": result["samples"][0]["trim"],
            "initial_count": result["samples"][0]["count"],
            "final_trim": result["final_trim"],
            "final_count": result["final_count"],
            "target_count": TARGET,
            "iterations": result["iterations"],
            "fw_pass": result["fw_pass"],
            "expected_pass": True,
            "wall_time_s": f"{wall:.3f}",
        }
    )


@pytest.fixture(scope="module")
def spice_trims():
    data = {}
    yield data
    passing = {name: row for name, row in data.items() if row["expected_pass"]}
    if len(passing) >= 3:
        trims = [row["final_trim"] for row in passing.values()]
        assert len(set(trims)) == len(trims), f"PASS corners should pick distinct trims: {data}"


@pytest.mark.parametrize(
    "corner,expected_pass",
    [
        ("nominal", True),
        ("slow", True),
        ("fast", True),
        ("extreme_slow", False),
    ],
)
def test_serv_dco(corner, expected_pass, spice_trims):
    spec = CORNERS[corner]
    assert spec["expected_pass"] is expected_pass
    build_dir = (EXAMPLE / "sim_build" / f"serv_{corner}").resolve()
    cir_path = build_dir / "dco.cir"
    render_netlist(cir_path, spec, tran_step="0.2ns", tran_stop="100us")

    t0 = time.perf_counter()
    result = _run(
        build_dir=build_dir,
        sources=_local_sources(EXAMPLE / "rtl" / "dco_core.v"),
        extra_env={
            "SPICE_NETLIST": str(cir_path),
            "HDL_INSTANCE": "top.u_dco",
            "VCC": str(spec["vdd"]),
            "CORNER_NAME": corner,
            "CORNER_LABEL": spec["label"],
            "CORNER_VDD": str(spec["vdd"]),
            "CORNER_TEMP": str(spec["temp"]),
            "EXPECTED_PASS": "1" if expected_pass else "0",
        },
        test_args=["-M", spicebind.get_lib_dir(), "-m", "spicebind_vpi"],
    )
    wall = time.perf_counter() - t0
    spice_trims[corner] = {
        "final_trim": result["final_trim"],
        "final_count": result["final_count"],
        "expected_pass": expected_pass,
        "fw_pass": result["fw_pass"],
        "wall_time_s": wall,
    }
    _append_csv(
        {
            "case": corner,
            "vdd": spec["vdd"],
            "temperature": spec["temp"],
            "initial_trim": result["samples"][0]["trim"],
            "initial_count": result["samples"][0]["count"],
            "final_trim": result["final_trim"],
            "final_count": result["final_count"],
            "target_count": TARGET,
            "iterations": result["iterations"],
            "fw_pass": result["fw_pass"],
            "expected_pass": expected_pass,
            "wall_time_s": f"{wall:.3f}",
        }
    )
