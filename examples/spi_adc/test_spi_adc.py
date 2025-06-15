import os
import pathlib

os.environ.setdefault("COCOTB_RESOLVE_X", "ZEROS")
import cocotb
from cocotb.triggers import Timer
from cocotbext.spi import SpiBus, SpiMaster, SpiConfig
from cocotb.runner import get_runner
import spicebind

@cocotb.test()
async def run_test(dut):
    bus = SpiBus.from_entity(dut)
    master = SpiMaster(bus, SpiConfig(sclk_freq=1e6))

    dut.vin.value = 1.0
    await Timer(1, units="us")

    # range 1V
    await master.write([0x00])
    await master.read()
    await Timer(100, units="ns")
    await master.write([0x00])  # capture new code
    await master.read()
    await master.write([0x00])  # shift out updated code
    code = (await master.read())[0]
    dut._log.info(f"range=1V code={code}")
    dut._log.info(f"range bits {int(dut.range.value)}")
    assert code == 255

    # range 2V
    await master.write([0x01])
    await master.read()
    await Timer(100, units="ns")
    await master.write([0x01])
    await master.read()
    await master.write([0x01])
    code = (await master.read())[0]
    dut._log.info(f"range=2V code={code}")
    dut._log.info(f"range bits {int(dut.range.value)}")
    assert 125 <= code <= 130

    # range 3.3V
    await master.write([0x02])
    await master.read()
    await Timer(100, units="ns")
    await master.write([0x02])
    await master.read()
    await master.write([0x02])
    code = (await master.read())[0]
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
