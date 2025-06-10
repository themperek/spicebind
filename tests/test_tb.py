import cocotb
from cocotb.triggers import Timer, Join, Combine
from cocotb.runner import get_runner
import os
from pathlib import Path
import random
import spicebind

async def run_adc_test(dut):

    dut.adc_in.value = 0.0
    await Timer(20, units="ns")
    assert dut.adc_out.value == 0

    dut.adc_in.value = 1.0
    await Timer(20, units="ns")
    assert dut.adc_out.value == 255

    dut.adc_in.value = 0.0
    await Timer(20, units="ns")
    assert dut.adc_out.value == 0

    expected = [0, 1, 3, 7, 15, 31, 63, 127, 255, 255, 255]
    dut.adc_in.value = 1.0
    for i in range(10):
        await Timer(2, units="ns")
        assert int(dut.adc_out.value) == expected[i]

    expected = [0b11111111, 0b11111110, 0b11111100, 0b11111000, 0b11110000, 0b11100000, 0b11000000, 0b10000000, 0b00000000, 0b00000000]
    dut.adc_in.value = 0.0
    for i in range(10):
        await Timer(2, units="ns")
        assert int(dut.adc_out.value) == expected[i]

    for i in range(1000):
        dut.adc_in.value = i * 0.001 - 0.00001
        await Timer(random.randint(20, 30), units="ns")
        assert int(dut.adc_in.value / (1 / 256)) == int(dut.adc_out.value)

    for i in range(1000):
        dut.adc_in.value = 1 - i * 0.001 - 0.00001
        await Timer(random.randint(20, 30), units="ns")
        assert int(dut.adc_in.value / (1 / 256)) == int(dut.adc_out.value)


async def run_dac_test(dut):

    dut.dac_in.value = 0
    await Timer(11, units="ns")
    assert abs(dut.dac_out.value - 0.0) < 1e-6

    dut.dac_in.value = 255
    await Timer(11, units="ns")
    assert abs(dut.dac_out.value - 1.0) < 1e-6

    for i in range(256):
        dut.dac_in.value = i
        await Timer(random.randint(8, 100), units="ns")
        assert int(dut.dac_in.value) == int((dut.dac_out.value - 0.00001) / (1 / 256))

    for i in reversed(range(256)):
        dut.dac_in.value = i
        await Timer(random.randint(8, 100), units="ns")
        assert int(dut.dac_in.value) == int((dut.dac_out.value - 0.00001) / (1 / 256))

async def run_pwm_test(dut):
    dut.pwm_in.value = 0
    await Timer(10, units="us")
    assert abs(dut.pwm_out.value - 0.0) < 1e-6
    
    dut.pwm_in.value = 1
    await Timer(10, units="us")
    assert abs(dut.pwm_out.value - 1.0) < 1e-6
    
    async def pwm_ctrl(duty):
        for i in range(100):
                dut.pwm_in.value = 1
                await Timer(duty, units="ns")
                dut.pwm_in.value = 0
                await Timer(100-duty, units="ns")
    
    await pwm_ctrl(50)
    assert dut.pwm_out.value == 'x'
    
    await pwm_ctrl(20)
    assert dut.pwm_out.value == 0

    await pwm_ctrl(80)
    assert dut.pwm_out.value == 1


@cocotb.test()
async def run_test(dut):

    adc_task = await cocotb.start(run_adc_test(dut))
    dac_task = await cocotb.start(run_dac_test(dut))
    pwm_task = await cocotb.start(run_pwm_test(dut))

    await Combine(adc_task, dac_task, pwm_task)


def test_tb():
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent
    sources = [proj_path / "tb.sv"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="tb",
        always=True,
    )

    runner.test(
        hdl_toplevel="tb",
        test_module="test_tb,",
        test_args=["-M", spicebind.get_lib_dir(), "-m", "spicebind_vpi"],
        extra_env={"SPICE_NETLIST": str(proj_path / "test.cir"), "HDL_INSTANCE": "tb.test_cir"},
    )


if __name__ == "__main__":
    test_tb()
