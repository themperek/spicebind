import os
import subprocess
from pathlib import Path

import pytest
import spicebind


def run_sv_test(vcc: float, *, expect_failure: bool = False) -> None:
    test_dir = Path(__file__).resolve().parent
    args = spicebind.cocotb_vpi_args()
    sim = args["sim"]
    build_dir = test_dir / "sim_build" / sim / "sv" / f"VCC={vcc}"
    if expect_failure:
        build_dir = build_dir.parent / f"VCC={vcc}-fail"
    build_dir.mkdir(parents=True, exist_ok=True)

    cir_path = build_dir / "test.cir"
    cir_path.write_text((test_dir / "test.cir").read_text().format(VCC=vcc))

    env = os.environ.copy()
    env.update(
        {
            "SPICE_NETLIST": str(cir_path),
            "HDL_INSTANCE": "tb_sv.test_cir",
            "VCC": str(vcc),
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
                "--trace",
                "--timescale",
                "1ns/1ps",
                "--top-module",
                "tb_sv",
                "--Wno-UNDRIVEN",
                "--Wno-UNUSED",
                "--Wno-WIDTHTRUNC",
                "--Wno-ZERODLY",
                f"-GVCC={vcc}",
                f"-GEXPECT_FAILURE={int(expect_failure)}",
                "--Mdir",
                str(obj_dir),
                "-o",
                "Vtb_sv",
                str(test_dir / "tb_sv.sv"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                f"verilator failed:\n{compile_result.stdout}\n{compile_result.stderr}"
            )
        cmd = [str(obj_dir / "Vtb_sv"), f"+verilator+vpi+{vpi}"]
    else:
        vvp_path = build_dir / "tb_sv.vvp"
        compile_result = subprocess.run(
            [
                "iverilog",
                "-g2012",
                "-o",
                str(vvp_path),
                "-s",
                "tb_sv",
                f"-Ptb_sv.VCC={vcc}",
                f"-Ptb_sv.EXPECT_FAILURE={int(expect_failure)}",
                str(test_dir / "tb_sv.sv"),
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

    try:
        result = subprocess.run(
            cmd,
            cwd=build_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
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


@pytest.mark.parametrize("vcc", [1.0, 1.8, 3.3])
def test_tb_sv(vcc):
    run_sv_test(vcc)


@pytest.mark.xfail(reason="Intentional SystemVerilog assertion failure", strict=True)
def test_tb_sv_failure():
    run_sv_test(1.0, expect_failure=True)
