import os
import pathlib

os.environ.setdefault("COCOTB_RESOLVE_X", "ZEROS")
import cocotb
import cocotb.clock as cocotb_clock
from cocotb.types import Logic
from cocotb.triggers import Timer

# cocotb 2.0 removed BaseClock, but cocotbext-spi 0.5.0 still imports it.
if not hasattr(cocotb_clock, "BaseClock"):
    class BaseClock:
        def __init__(self, signal):
            self.signal = signal

    cocotb_clock.BaseClock = BaseClock

# cocotb 2.x replaced Logic.integer with int(Logic).
if not hasattr(Logic, "integer"):
    Logic.integer = property(lambda value: int(value))

from cocotbext.spi import SpiBus, SpiMaster, SpiConfig
from cocotb_tools.runner import get_runner
import spicebind


@cocotb.test()
async def run_test(dut):
    bus = SpiBus.from_entity(dut)
    master = SpiMaster(bus, SpiConfig(sclk_freq=1e6))

    async def get_code():
        await master.write([0x00])  # trigger sampling
        await master.write([0x00])  # ransfer code
        code = (await master.read())[1]
        return code

    dut.vin.value = 1.0
    await Timer(0.1, unit="us")
    code = await get_code()
    dut._log.info(f"code={code}")
    assert code == 255
    
    dut.vin.value = 0.75
    await Timer(0.1, unit="us")
    code = await get_code()
    dut._log.info(f"code={code}")
    assert abs(code - 191) < 2

    dut.vin.value = 0.25
    await Timer(0.1, unit="us")
    code = await get_code()
    dut._log.info(f"code={code}")
    assert abs(code - 63) < 2

    dut.vin.value = 0.0
    await Timer(0.1, unit="us")
    code = await get_code()
    dut._log.info(f"code={code}")
    assert code == 0
    
    await Timer(1, unit="us") 

    dut.vin.value = 1.0
    await Timer(1, unit="us")

    # range 1V
    await master.write([0x00])
    await master.read()
    await Timer(100, unit="ns")
    code = await get_code()
    dut._log.info(f"range=1V code={code}")
    dut._log.info(f"range bits {int(dut.range.value)}")
    assert code == 255

    # range 2V
    await master.write([0x01])
    await master.read()
    await Timer(100, unit="ns")
    code = await get_code()
    dut._log.info(f"range=2V code={code}")
    dut._log.info(f"range bits {int(dut.range.value)}")
    assert 125 <= code <= 130

    # range 3.3V
    await master.write([0x02])
    await master.read()
    await Timer(100, unit="ns")
    code = await get_code()
    dut._log.info(f"range=3.3V code={code}")
    dut._log.info(f"range bits {int(dut.range.value)}")
    assert 75 <= code <= 80


def test_spi_adc():
    sim = os.getenv("SIM", "icarus")
    proj_path = pathlib.Path(__file__).resolve().parent
    sources = [proj_path / "spi_adc.v"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="spi_adc",
        always=True,
    )

    runner.test(
        hdl_toplevel="spi_adc",
        test_module="test_spi_adc",
        test_args=["-M", spicebind.get_lib_dir(), "-m", "spicebind_vpi"],
        extra_env={
            "SPICE_NETLIST": str(proj_path / "spi_adc.cir"),
            "HDL_INSTANCE": "spi_adc.adc_inst",
            "COCOTB_RESOLVE_X": "ZEROS",
        },
    )


if __name__ == "__main__":
    test_spi_adc()
