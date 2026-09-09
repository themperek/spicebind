"""No-cocotb HDL timing on the 100 ps delay fixture (Icarus and Verilator).

``quiet_edges`` waits one extra analog step after each delay (``#2; #0.1``)
because a plain ``#2`` can resume before VPI puts analog outputs. The
``quiet_edges_raw`` / ``quiet_edges_nba`` / ``raw_2ns`` cases are the user
forms (``#2`` and ``#2; #0``) and are expected to fail until that put
happens before HDL processes resume.

``test_timing_timescale`` prepends `` `timescale `` combinations onto
``tb_timing_scale.v``, which uses ``#1ns`` / ``#2ns`` so the analog 2 ns
delay does not track the module time unit.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import spicebind

TEST_DIR = Path(__file__).resolve().parent

_XFAIL_HDL_RAW = pytest.mark.xfail(
    reason="Verilog #2 / #2; #0 resume before VPI puts analog outputs; delayed bit is still 0",
    strict=True,
)

SV_CASES = [
    "quiet_edges",
    pytest.param("quiet_edges_raw", marks=_XFAIL_HDL_RAW),
    pytest.param("quiet_edges_nba", marks=_XFAIL_HDL_RAW),
    "between_edges",
    "before_at",
    "dac_edges",
    "dac_before_at",
    "offgrid",
    "short_pulse",
    "repeat_dac",
]

V_CASES = [
    pytest.param(0, id="quiet_edge"),
    pytest.param(1, id="hammer_edge"),
    pytest.param(2, id="offgrid"),
    pytest.param(3, id="short_pulse"),
    pytest.param(4, id="raw_2ns", marks=_XFAIL_HDL_RAW),
]


def _run_vpi_hdl(
    *,
    source: Path,
    top: str,
    instance: str,
    cir_template: Path,
    case_plusarg: str,
    extra_iverilog: list[str] | None = None,
    extra_verilator: list[str] | None = None,
    timescale: str = "1ns/1ps",
    build_name: str | None = None,
    timeout: int = 60,
) -> None:
    args = spicebind.cocotb_vpi_args()
    sim = args["sim"]
    build_dir = TEST_DIR / "sim_build" / sim / (build_name or top)
    build_dir.mkdir(parents=True, exist_ok=True)
    cir_path = build_dir / "test.cir"
    cir_path.write_text(cir_template.read_text().format(VCC=1.0))

    env = os.environ.copy()
    env.update(
        {
            "SPICE_NETLIST": str(cir_path),
            "HDL_INSTANCE": instance,
            "VCC": "1.0",
        }
    )

    if sim == "verilator":
        vpi = spicebind.get_vpi_module_path()
        if not vpi:
            raise RuntimeError("spicebind_vpi.vpi not found")
        obj_dir = build_dir / "obj_dir"
        compile_result = subprocess.run(
            [
                "verilator",
                "--binary",
                "-j",
                "0",
                "--vpi",
                "--timing",
                "--public-flat-rw",
                "--fno-inline",
                "--timescale",
                timescale,
                "--timescale-override",
                timescale,
                "--top-module",
                top,
                "--Wno-UNDRIVEN",
                "--Wno-UNUSED",
                "--Wno-WIDTHTRUNC",
                "--Wno-WIDTHEXPAND",
                "--Wno-ZERODLY",
                "--Wno-TIMESCALEMOD",
                "--Mdir",
                str(obj_dir),
                "-o",
                f"V{top}",
                *(extra_verilator or []),
                str(source),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                f"verilator failed:\n{compile_result.stdout}\n{compile_result.stderr}"
            )
        cmd = [str(obj_dir / f"V{top}"), f"+verilator+vpi+{vpi}"]
        if case_plusarg:
            cmd.append(case_plusarg)
    else:
        vvp_path = build_dir / f"{top}.vvp"
        compile_result = subprocess.run(
            [
                "iverilog",
                "-g2012",
                "-o",
                str(vvp_path),
                "-s",
                top,
                *(extra_iverilog or []),
                str(source),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                f"iverilog failed:\n{compile_result.stdout}\n{compile_result.stderr}"
            )
        cmd = [
            "vvp",
            "-M",
            spicebind.get_lib_dir(),
            "-m",
            "spicebind_vpi",
            str(vvp_path),
        ]
        if case_plusarg:
            cmd.append(case_plusarg)

    try:
        result = subprocess.run(
            cmd,
            cwd=build_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(
            f"{sim} timed out after {exc.timeout}s:\n{exc.stdout}\n{exc.stderr}"
        ) from exc
    if result.returncode != 0:
        raise AssertionError(
            f"{sim} failed with exit code {result.returncode}:\n"
            f"{result.stdout}\n{result.stderr}"
        )


@pytest.mark.parametrize("case", SV_CASES)
def test_timing_edges_sv(case):
    _run_vpi_hdl(
        source=TEST_DIR / "tb_timing_edges.sv",
        top="tb_timing_edges",
        instance="tb_timing_edges.test_cir",
        cir_template=TEST_DIR / "timing_edges.cir",
        case_plusarg=f"+CASE={case}",
    )


@pytest.mark.parametrize("case_id", V_CASES)
def test_timing_bit_v(case_id):
    _run_vpi_hdl(
        source=TEST_DIR / "tb_timing_bit.v",
        top="tb_timing_bit",
        instance="tb_timing_bit.test_cir",
        cir_template=TEST_DIR / "timing_bit.cir",
        case_plusarg=f"+CASE={case_id}",
    )


# Unit / precision pairs. Delays in tb_timing_scale.v are #1ns / #2ns so the
# analog 2 ns delay stays 2 ns when the module unit is not 1 ns.
# 1ns/1ps and 1ps/1ps share precision; the rest change unit, precision, or both.
_TIMESCALES = [
    "1ns/1ps",
    "1ps/1ps",
    "1ns/100ps",
    "1ns/1ns",
    "1us/1ns",
    "10ns/1ps",
]


@pytest.mark.parametrize("timescale", _TIMESCALES)
def test_timing_timescale(timescale):
    stamp = timescale.replace("/", "_")
    sim = spicebind.cocotb_vpi_args()["sim"]
    gen = TEST_DIR / "sim_build" / sim / f"tb_timing_scale_{stamp}"
    gen.mkdir(parents=True, exist_ok=True)
    source = gen / "tb_timing_scale.v"
    source.write_text(f"`timescale {timescale}\n\n" + (TEST_DIR / "tb_timing_scale.v").read_text())
    _run_vpi_hdl(
        source=source,
        top="tb_timing_scale",
        instance="tb_timing_scale.test_cir",
        cir_template=TEST_DIR / "timing_bit.cir",
        case_plusarg="",
        timescale=timescale,
        build_name=f"tb_timing_scale_{stamp}",
    )
