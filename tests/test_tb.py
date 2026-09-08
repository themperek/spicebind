import cocotb
from cocotb.triggers import ReadWrite, Timer
from cocotb_tools.runner import get_runner
import os
from pathlib import Path
import random
import spicebind
import pytest


def _sim() -> str:
    return os.getenv("SIM", "icarus")


async def run_adc_test(dut):
    dut.adc_in.value = 0.0
    await Timer(20, unit="ns")
    await ReadWrite()
    assert dut.adc_out.value == 0

    dut.adc_in.value = 1.0
    await Timer(20, unit="ns")
    await ReadWrite()
    assert dut.adc_out.value == 255

    dut.adc_in.value = 0.0
    await Timer(20, unit="ns")
    await ReadWrite()
    assert dut.adc_out.value == 0

    # Bits arrive at 2, 4, … 16 ns. Sample at 1.5, 3.5, … ns (between 1 ns
    # spice ticks). Checking on an integer ns races Icarus AfterDelay vs
    # cocotb ReadWrite and the concurrent DAC task, so this flake is
    # seed-dependent (got 0, expected 1 at 63.00 ns).
    expected = [0, 1, 3, 7, 15, 31, 63, 127, 255, 255]
    dut.adc_in.value = 1.0
    await Timer(1.5, unit="ns")
    await ReadWrite()
    for i, exp in enumerate(expected):
        got = int(dut.adc_out.value)
        assert got == exp, f"i={i} dut.adc_out.value={got} expected={exp}"
        await Timer(2, unit="ns")
        await ReadWrite()

    expected = [
        0b11111111,
        0b11111110,
        0b11111100,
        0b11111000,
        0b11110000,
        0b11100000,
        0b11000000,
        0b10000000,
        0b00000000,
        0b00000000,
    ]
    dut.adc_in.value = 0.0
    await Timer(1.5, unit="ns")
    await ReadWrite()
    for i, exp in enumerate(expected):
        got = int(dut.adc_out.value)
        assert got == exp, f"i={i} dut.adc_out.value={got} expected={exp}"
        await Timer(2, unit="ns")
        await ReadWrite()

    for i in range(1000):
        await ReadWrite()
        dut.adc_in.value = i * 0.001 - 0.00001
        await Timer(random.randint(20, 30), unit="ns")
        await ReadWrite()
        assert int(dut.adc_in.value / (1 / 256)) == int(dut.adc_out.value)

    for i in range(1000):
        await ReadWrite()
        dut.adc_in.value = 1 - i * 0.001 - 0.00001
        await Timer(random.randint(20, 30), unit="ns")
        await ReadWrite()
        assert int(dut.adc_in.value / (1 / 256)) == int(dut.adc_out.value)


async def run_dac_test(dut):
    vcc = float(os.getenv("VCC", "1.0"))

    dut.dac_in.value = 0
    await Timer(11, unit="ns")
    await ReadWrite()
    assert abs(dut.dac_out.value - 0.0) < 1e-6

    dut.dac_in.value = 255
    await Timer(11, unit="ns")
    await ReadWrite()
    assert abs(dut.dac_out.value - vcc) < 1e-6

    for i in range(256):
        await ReadWrite()
        dut.dac_in.value = i
        await Timer(random.randint(8, 100), unit="ns")
        await ReadWrite()
        assert int(dut.dac_in.value) == int((dut.dac_out.value - 0.00001) / (vcc / 256))

    for i in reversed(range(256)):
        await ReadWrite()
        dut.dac_in.value = i
        await Timer(random.randint(8, 100), unit="ns")
        await ReadWrite()
        assert int(dut.dac_in.value) == int((dut.dac_out.value - 0.00001) / (vcc / 256))


async def run_pwm_test(dut):
    dut.pwm_in.value = 0
    await Timer(10, unit="us")
    await ReadWrite()
    assert abs(int(dut.pwm_out.value) - 0.0) < 1e-6

    dut.pwm_in.value = 1
    await Timer(10, unit="us")
    await ReadWrite()
    assert abs(int(dut.pwm_out.value) - 1.0) < 1e-6

    async def pwm_ctrl(duty):
        for i in range(100):
            await ReadWrite()
            dut.pwm_in.value = 1
            await Timer(duty, unit="ns")
            dut.pwm_in.value = 0
            await Timer(100 - duty, unit="ns")
            await ReadWrite()

    await pwm_ctrl(50)
    if _sim() == "verilator":
        assert dut.pwm_out.value in (0, 1, "x")
    else:
        assert dut.pwm_out.value == "x"

    await pwm_ctrl(20)
    assert dut.pwm_out.value == 0

    await pwm_ctrl(80)
    assert dut.pwm_out.value == 1


@cocotb.test()
async def run_test(dut):
    adc_task = cocotb.start_soon(run_adc_test(dut))
    dac_task = cocotb.start_soon(run_dac_test(dut))
    pwm_task = cocotb.start_soon(run_pwm_test(dut))

    await adc_task
    await dac_task
    await pwm_task


@pytest.mark.parametrize("vcc", [1.0, 1.8, 3.3])
def test_tb(vcc):
    args = spicebind.cocotb_vpi_args()
    sim = args["sim"]

    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "tb.sv"]
    cir_template = proj_path / "test.cir"

    build_dir = (proj_path / "sim_build" / sim / f"VCC={vcc}").resolve()
    build_dir.mkdir(parents=True, exist_ok=True)

    cir_path = build_dir / "test.cir"
    cir_path.write_text(cir_template.read_text().format(VCC=vcc))

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="tb",
        always=True,
        build_dir=build_dir,
        build_args=args["build_args"],
        timescale=("1ns", "1ps"),
        waves=args["waves"],
    )

    runner.test(
        hdl_toplevel="tb",
        test_module="test_tb,",
        test_args=args["test_args"],
        plusargs=args["plusargs"],
        extra_env={
            "SPICE_NETLIST": str(cir_path),
            "HDL_INSTANCE": "tb.test_cir",
            "VCC": str(vcc),
        },
    )


if __name__ == "__main__":
    test_tb(1.8)
