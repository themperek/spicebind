"""Delay-chain timing as a user would write it (Icarus and Verilator).

Analog bits in ``timing_edges.cir`` are delayed by 2, 4, … 16 ns. Waiting those
times in HDL must show the matching code. Concurrent DAC/PWM activity must not
move the bits. Samples are taken at the delay times themselves, not on a
workaround grid.

Cocotb sample styles after ``Timer``:

- none: read as soon as the timer fires.
- ``ReadOnly``: wait until this timestep is stable, then read.
- ``ReadWrite``: wait through the analog VPI put (stronger than most benches).

All three see the delayed bits at the exact 2, 4, … ns edges. A Verilog
``#2; x = adc_out`` does *not* (see ``test_timing_hdl.py`` xfails): the
HDL process can resume before VPI puts analog outputs.
"""

from __future__ import annotations

import os
from pathlib import Path

import cocotb
import pytest
import spicebind
from cocotb.triggers import ReadOnly, ReadWrite, Timer
from cocotb_tools.runner import get_runner

# After each 2 ns analog delay has elapsed.
RISE_AFTER_DELAY = [1, 3, 7, 15, 31, 63, 127, 255]
FALL_AFTER_DELAY = [0xFE, 0xFC, 0xF8, 0xF0, 0xE0, 0xC0, 0x80, 0x00]

# Midway between delay edges (1.5, 3.5, … ns after the input step).
RISE_BETWEEN = [0, 1, 3, 7, 15, 31, 63, 127, 255, 255]
FALL_BETWEEN = [0xFF, 0xFE, 0xFC, 0xF8, 0xF0, 0xE0, 0xC0, 0x80, 0x00, 0x00]


def _sim() -> str:
    return os.getenv("SIM", "icarus")


def _code(dut) -> int:
    return int(dut.adc_out.value)


async def _settle_zero(dut):
    dut.adc_in.value = 0.0
    dut.dac_in.value = 0
    await Timer(20, unit="ns")
    await ReadWrite()
    assert _code(dut) == 0, f"settle: adc_out={_code(dut)} expected 0"


async def _await_sample(mode: str | None):
    if mode == "rw":
        await ReadWrite()
    elif mode == "ro":
        await ReadOnly()


async def _dac_pwm_hammer(dut, running: list[bool], period_ns: float):
    bit = 0
    while running[0]:
        dut.dac_in.value = 0x55 if bit == 0 else 0xAA
        dut.pwm_in.value = bit
        bit ^= 1
        await Timer(period_ns, unit="ns")
        await ReadWrite()


async def _sample_chain(dut, first_ns, step_ns, expected, sample: str | None, label: str) -> list[str]:
    findings = []
    t = 0.0
    for i, exp in enumerate(expected):
        wait = first_ns if i == 0 else step_ns
        await Timer(wait, unit="ns")
        t += wait
        await _await_sample(sample)
        got = _code(dut)
        if got != exp:
            findings.append(
                f"{label} i={i} t={t:g}ns got={got} expected={exp} sample={sample} sim={_sim()}"
            )
    return findings


async def _walk_edges(dut, sample: str | None, label: str, hammer_ns=None) -> list[str]:
    await _settle_zero(dut)
    running = [True]
    hammer = None
    if hammer_ns is not None:
        hammer = cocotb.start_soon(_dac_pwm_hammer(dut, running, hammer_ns))
    findings = []
    dut.adc_in.value = 1.0
    findings += await _sample_chain(dut, 2.0, 2.0, RISE_AFTER_DELAY, sample, f"{label}-rise")
    dut.adc_in.value = 0.0
    findings += await _sample_chain(dut, 2.0, 2.0, FALL_AFTER_DELAY, sample, f"{label}-fall")
    if hammer is not None:
        running[0] = False
        await hammer
    return findings


async def _just_before_and_at(dut, sample: str | None, label: str, hammer_ns=None) -> list[str]:
    await _settle_zero(dut)
    running = [True]
    hammer = None
    if hammer_ns is not None:
        hammer = cocotb.start_soon(_dac_pwm_hammer(dut, running, hammer_ns))
    findings = []
    dut.adc_in.value = 1.0
    await Timer(1.9, unit="ns")
    await _await_sample(sample)
    got = _code(dut)
    if got != 0:
        findings.append(f"{label}-before-2ns got={got} expected=0 sample={sample} sim={_sim()}")
    await Timer(0.1, unit="ns")
    await _await_sample(sample)
    got = _code(dut)
    if got != 1:
        findings.append(f"{label}-at-2ns got={got} expected=1 sample={sample} sim={_sim()}")
    await Timer(1.9, unit="ns")
    await _await_sample(sample)
    got = _code(dut)
    if got != 1:
        findings.append(f"{label}-before-4ns got={got} expected=1 sample={sample} sim={_sim()}")
    await Timer(0.1, unit="ns")
    await _await_sample(sample)
    got = _code(dut)
    if got != 3:
        findings.append(f"{label}-at-4ns got={got} expected=3 sample={sample} sim={_sim()}")
    if hammer is not None:
        running[0] = False
        await hammer
    return findings


@cocotb.test()
async def delay_on_edge_readwrite_quiet(dut):
    """After 2, 4, … ns a user who waits those delays sees the matching bits."""
    findings = await _walk_edges(dut, "rw", "edge-rw-quiet")
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_on_edge_readonly_quiet(dut):
    """Same exact edges, sample in ReadOnly (stable-read, no extra analog wait)."""
    findings = await _walk_edges(dut, "ro", "edge-ro-quiet")
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_on_edge_timer_only_quiet(dut):
    """Same edge samples with Timer only, no ReadWrite/ReadOnly."""
    findings = await _walk_edges(dut, None, "edge-timer-quiet")
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_between_edges_quiet(dut):
    """1.5, 3.5, … ns: still between delay edges."""
    await _settle_zero(dut)
    findings = []
    dut.adc_in.value = 1.0
    findings += await _sample_chain(dut, 1.5, 2.0, RISE_BETWEEN, "rw", "rise-between-quiet")
    dut.adc_in.value = 0.0
    findings += await _sample_chain(dut, 1.5, 2.0, FALL_BETWEEN, "rw", "fall-between-quiet")
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_between_edges_readonly_quiet(dut):
    """Between-edge samples in ReadOnly."""
    await _settle_zero(dut)
    findings = []
    dut.adc_in.value = 1.0
    findings += await _sample_chain(dut, 1.5, 2.0, RISE_BETWEEN, "ro", "rise-between-ro")
    dut.adc_in.value = 0.0
    findings += await _sample_chain(dut, 1.5, 2.0, FALL_BETWEEN, "ro", "fall-between-ro")
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_between_edges_timer_only_quiet(dut):
    """Between-edge samples with Timer only."""
    await _settle_zero(dut)
    findings = []
    dut.adc_in.value = 1.0
    findings += await _sample_chain(dut, 1.5, 2.0, RISE_BETWEEN, None, "rise-between-timer")
    dut.adc_in.value = 0.0
    findings += await _sample_chain(dut, 1.5, 2.0, FALL_BETWEEN, None, "fall-between-timer")
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_on_edge_readwrite_dac_1ns(dut):
    """Exact delay edges while DAC/PWM toggle every 1 ns."""
    findings = await _walk_edges(dut, "rw", "edge-rw-dac1", hammer_ns=1.0)
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_on_edge_readonly_dac_1ns(dut):
    """Exact delay edges, ReadOnly samples, with a 1 ns DAC/PWM hammer."""
    findings = await _walk_edges(dut, "ro", "edge-ro-dac1", hammer_ns=1.0)
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_on_edge_timer_only_dac_1ns(dut):
    """Exact delay edges, Timer only, with 1 ns DAC/PWM hammer."""
    findings = await _walk_edges(dut, None, "edge-timer-dac1", hammer_ns=1.0)
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_between_edges_dac_1ns(dut):
    """Between-edge samples while DAC/PWM toggle every 1 ns."""
    await _settle_zero(dut)
    running = [True]
    hammer = cocotb.start_soon(_dac_pwm_hammer(dut, running, 1.0))
    findings = []
    dut.adc_in.value = 1.0
    findings += await _sample_chain(dut, 1.5, 2.0, RISE_BETWEEN, "rw", "rise-between-dac1")
    dut.adc_in.value = 0.0
    findings += await _sample_chain(dut, 1.5, 2.0, FALL_BETWEEN, "rw", "fall-between-dac1")
    running[0] = False
    await hammer
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_on_edge_dac_offgrid(dut):
    """Exact delay edges with DAC/PWM on a 0.7 ns grid."""
    findings = await _walk_edges(dut, "rw", "edge-rw-dac07", hammer_ns=0.7)
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_between_edges_dac_offgrid(dut):
    """Between-edge samples with DAC/PWM on a 0.7 ns grid."""
    await _settle_zero(dut)
    running = [True]
    hammer = cocotb.start_soon(_dac_pwm_hammer(dut, running, 0.7))
    findings = []
    dut.adc_in.value = 1.0
    findings += await _sample_chain(dut, 1.5, 2.0, RISE_BETWEEN, "rw", "rise-between-dac07")
    dut.adc_in.value = 0.0
    findings += await _sample_chain(dut, 1.5, 2.0, FALL_BETWEEN, "rw", "fall-between-dac07")
    running[0] = False
    await hammer
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_just_before_and_at_edge(dut):
    """One analog step (100 ps) before a 2 ns delay the bit is still clear; at 2 ns it is set."""
    findings = await _just_before_and_at(dut, "rw", "before-at-rw")
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_just_before_and_at_edge_readonly(dut):
    """Same 1.9 / 2.0 ns checks sampled in ReadOnly."""
    findings = await _just_before_and_at(dut, "ro", "before-at-ro")
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_just_before_and_at_edge_timer_only(dut):
    """Same 1.9 / 2.0 ns checks with Timer only."""
    findings = await _just_before_and_at(dut, None, "before-at-timer")
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_just_before_and_at_edge_with_dac(dut):
    """Same pre/at-edge checks with a 1 ns DAC hammer."""
    findings = await _just_before_and_at(dut, "rw", "before-at-dac", hammer_ns=1.0)
    if findings:
        raise AssertionError("\n".join(findings))


@cocotb.test()
async def delay_just_before_and_at_falling_edge(dut):
    """After a settled high, the LSB stays set at 1.9 ns and clears at 2 ns."""
    await _settle_zero(dut)
    dut.adc_in.value = 1.0
    await Timer(20, unit="ns")
    await ReadWrite()
    if _code(dut) != 255:
        raise AssertionError(f"settle-high got={_code(dut)} expected=255 sim={_sim()}")
    dut.adc_in.value = 0.0
    await Timer(1.9, unit="ns")
    await ReadWrite()
    got = _code(dut)
    if got != 255:
        raise AssertionError(f"fall-before-2ns got={got} expected=255 sim={_sim()}")
    await Timer(0.1, unit="ns")
    await ReadWrite()
    got = _code(dut)
    if got != 254:
        raise AssertionError(f"fall-at-2ns got={got} expected=254 sim={_sim()}")


@cocotb.test()
async def delay_edge_with_simultaneous_dac_step(dut):
    """An ADC step and a DAC write at the same time must not move the 2 ns edge."""
    await _settle_zero(dut)
    dut.adc_in.value = 1.0
    dut.dac_in.value = 0xA5
    await Timer(1.9, unit="ns")
    await ReadWrite()
    got = _code(dut)
    if got != 0:
        raise AssertionError(f"simultaneous-before-2ns got={got} expected=0 sim={_sim()}")
    await Timer(0.1, unit="ns")
    await ReadWrite()
    got = _code(dut)
    if got != 1:
        raise AssertionError(f"simultaneous-at-2ns got={got} expected=1 sim={_sim()}")


@cocotb.test()
async def delay_from_offgrid_input(dut):
    """A step at 0.37 ns still arrives 2 ns later, not rounded to a 1 ns tick."""
    await _settle_zero(dut)
    await Timer(0.37, unit="ns")
    dut.adc_in.value = 1.0
    await Timer(1.9, unit="ns")
    await ReadWrite()
    got = _code(dut)
    if got != 0:
        raise AssertionError(f"offgrid-before-2ns got={got} expected=0 sim={_sim()}")
    await Timer(0.1, unit="ns")
    await ReadWrite()
    got = _code(dut)
    if got != 1:
        raise AssertionError(f"offgrid-at-2ns got={got} expected=1 sim={_sim()}")


@cocotb.test()
async def short_pulse_shorter_than_delay(dut):
    """A 1 ns full-scale pulse must not set the 2 ns delayed LSB."""
    await _settle_zero(dut)
    dut.adc_in.value = 1.0
    await Timer(1.0, unit="ns")
    dut.adc_in.value = 0.0
    await Timer(5.0, unit="ns")
    await ReadWrite()
    got = _code(dut)
    if got != 0:
        raise AssertionError(f"short-pulse leftover adc_out={got} expected=0 sim={_sim()}")


@cocotb.test()
async def two_nanosecond_pulse_sets_lsb_then_clears(dut):
    """A pulse as wide as the first delay sets bit 0, then clears after 2 ns."""
    await _settle_zero(dut)
    dut.adc_in.value = 1.0
    await Timer(2.0, unit="ns")
    await ReadWrite()
    got = _code(dut)
    if got != 1:
        raise AssertionError(f"2ns-pulse at falling edge got={got} expected=1 sim={_sim()}")
    dut.adc_in.value = 0.0
    await Timer(2.0, unit="ns")
    await ReadWrite()
    got = _code(dut)
    if got != 0:
        raise AssertionError(f"2ns-pulse after delay got={got} expected=0 sim={_sim()}")


@cocotb.test()
async def repeated_edge_trials_with_dac(dut):
    """Twenty rise/fall walks on the exact delay edges under a 1 ns DAC hammer."""
    findings = []
    for trial in range(20):
        findings += await _walk_edges(dut, "rw", f"trial{trial}", hammer_ns=1.0)
    if findings:
        raise AssertionError(
            f"{len(findings)} mismatches in 20 trials\n" + "\n".join(findings[:40])
        )


_CASES = [
    "delay_on_edge_readwrite_quiet",
    "delay_on_edge_readonly_quiet",
    "delay_on_edge_timer_only_quiet",
    "delay_between_edges_quiet",
    "delay_between_edges_readonly_quiet",
    "delay_between_edges_timer_only_quiet",
    "delay_on_edge_readwrite_dac_1ns",
    "delay_on_edge_readonly_dac_1ns",
    "delay_on_edge_timer_only_dac_1ns",
    "delay_between_edges_dac_1ns",
    "delay_on_edge_dac_offgrid",
    "delay_between_edges_dac_offgrid",
    "delay_just_before_and_at_edge",
    "delay_just_before_and_at_edge_readonly",
    "delay_just_before_and_at_edge_timer_only",
    "delay_just_before_and_at_edge_with_dac",
    "delay_just_before_and_at_falling_edge",
    "delay_edge_with_simultaneous_dac_step",
    "delay_from_offgrid_input",
    "short_pulse_shorter_than_delay",
    "two_nanosecond_pulse_sets_lsb_then_clears",
    "repeated_edge_trials_with_dac",
]


@pytest.mark.parametrize("testcase", _CASES)
def test_timing_edges(testcase):
    args = spicebind.cocotb_vpi_args()
    sim = args["sim"]
    proj_path = Path(__file__).resolve().parent
    build_dir = (proj_path / "sim_build" / sim / "timing_edges").resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    cir_path = build_dir / "test.cir"
    cir_path.write_text((proj_path / "timing_edges.cir").read_text().format(VCC=1.0))

    runner = get_runner(sim)
    runner.build(
        sources=[proj_path / "tb.sv"],
        hdl_toplevel="tb",
        always=True,
        build_dir=build_dir,
        build_args=args["build_args"],
        timescale=("1ns", "1ps"),
        waves=args["waves"],
    )
    extra_env = {
        "SPICE_NETLIST": str(cir_path),
        "HDL_INSTANCE": "tb.test_cir",
        "VCC": "1.0",
        "COCOTB_TEST_FILTER": f"^{testcase}$",
    }
    runner.test(
        hdl_toplevel="tb",
        test_module="test_timing_edges,",
        test_args=args["test_args"],
        plusargs=args["plusargs"],
        extra_env=extra_env,
    )
