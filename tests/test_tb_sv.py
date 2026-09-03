import os
import subprocess
from pathlib import Path

import pytest
import spicebind


def run_sv_test(vcc: float, *, expect_failure: bool = False) -> None:
    test_dir = Path(__file__).resolve().parent
    build_dir = test_dir / "sim_build" / "sv" / f"VCC={vcc}"
    build_dir.mkdir(parents=True, exist_ok=True)

    cir_path = build_dir / "test.cir"
    cir_path.write_text((test_dir / "test.cir").read_text().format(VCC=vcc))

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

    env = os.environ.copy()
    env.update(
        {
            "SPICE_NETLIST": str(cir_path),
            "HDL_INSTANCE": "tb_sv.test_cir",
            "VCC": str(vcc),
        }
    )
    result = subprocess.run(
        [
            "vvp",
            "-M",
            spicebind.get_lib_dir(),
            "-m",
            "spicebind_vpi",
            str(vvp_path),
        ],
        cwd=build_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"vvp failed with exit code {result.returncode}:\n"
            f"{result.stdout}\n{result.stderr}"
        )


@pytest.mark.parametrize("vcc", [1.0, 1.8, 3.3])
def test_tb_sv(vcc):
    run_sv_test(vcc)


@pytest.mark.xfail(reason="Intentional SystemVerilog assertion failure", strict=True)
def test_tb_sv_failure():
    run_sv_test(1.0, expect_failure=True)
