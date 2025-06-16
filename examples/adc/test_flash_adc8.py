"""
Coherent-sampling + static-linearity testbench for the behavioural 8-bit flash
ADC (INL/DNL plots).
"""

import math
import pathlib
import os

import cocotb
from cocotb.triggers import Timer
from cocotb.runner import get_runner
import spicebind

import numpy as np
from numpy.fft import rfft, rfftfreq
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# User-tunable parameters
# -----------------------------------------------------------------------------
VREF = 1.0  # full-scale voltage of the ADC model
FS_NS = 20  # sample rate in [ns]
FS = int(1 / FS_NS * 1e9)  # sample rate [Hz] (informational only)

N_SAMPLES = 4096  # record length for FFT (power of two)
K_BIN = 601  # coherent-tone bin index (1 ≤ K < N/2)
F_IN = K_BIN * FS / N_SAMPLES

WINDOW = np.ones(N_SAMPLES)  # rectangular → unity coherent gain
DB_EPS = 1e-20  # prevents log10(0)

# Ramp for code-density test (static linearity)
RAMP_SAMPLES = 65_536  # ≥ 256× codes for fine resolution

# -----------------------------------------------------------------------------
# Dynamic-range metrics (unchanged, but isolated for reuse)
# -----------------------------------------------------------------------------


def calc_dynamic_metrics(codes: np.ndarray, vref: float = VREF):
    """Return SINAD, ENOB, SNR, THD, SFDR and the spectrum."""

    analog = (codes.astype(np.float64) + 0.5) * vref / 256.0
    analog -= np.mean(analog)

    spec = np.abs(rfft(analog * WINDOW)) ** 2
    freqs = rfftfreq(N_SAMPLES, d=1 / FS)

    fund_bin = np.argmax(spec[1:]) + 1
    fund_power = spec[fund_bin]

    other_bins = np.arange(1, len(spec))
    other_bins = other_bins[other_bins != fund_bin]
    nd_power = np.sum(spec[other_bins])

    harmonics = [spec[h * fund_bin] for h in range(2, 6) if h * fund_bin < len(spec)]
    thd_power = np.sum(harmonics) if harmonics else 0.0
    noise_power = max(nd_power - thd_power, 1e-30)
    thd_power = max(thd_power, 1e-30)

    sinad = 10 * np.log10(fund_power / (noise_power + thd_power))
    snr = 10 * np.log10(fund_power / noise_power)
    thd = 10 * np.log10(fund_power / thd_power)
    sfdr = 10 * np.log10(fund_power / max(harmonics)) if harmonics else float("nan")
    enob = (sinad - 1.76) / 6.02

    assert 7.5 <= enob <= 8.0

    return {"SINAD": sinad, "SNR": snr, "THD": thd, "SFDR": sfdr, "ENOB": enob, "freqs": freqs, "spec": spec}


# -----------------------------------------------------------------------------
# INL / DNL from a code-density ramp
# -----------------------------------------------------------------------------


def calc_inl_dnl(codes: np.ndarray, vref: float = VREF):
    """Return INL and DNL arrays (length 256).  Uses first-transition method."""

    n_codes = 256
    # 1. Find transition indices - first sample where code increases
    transitions = np.zeros(n_codes + 1)  # include 0 and VREF at ends
    transitions[0] = 0.0
    transitions[-1] = vref

    prev_code = codes[0]
    for i, code in enumerate(codes[1:], start=1):
        if code != prev_code:
            # record transition voltage
            transitions[code] = (i / (len(codes) - 1)) * vref
            prev_code = code
        if code == n_codes - 1 and prev_code == code:
            break  # reached top code

    # Fill any zeros (ideal ramp guarantees none, but be safe)
    for idx in range(1, n_codes):
        if transitions[idx] == 0:
            transitions[idx] = transitions[idx - 1]

    ideal_step = vref / n_codes

    # DNL[i] relates to code i (width between transitions i and i+1)
    dnl = (np.diff(transitions) / ideal_step) - 1.0  # length 256

    # INL[i] uses midpoint of code i
    mids_actual = (transitions[:-1] + transitions[1:]) / 2.0
    mids_ideal = (np.arange(n_codes) + 0.5) * ideal_step
    inl = (mids_actual - mids_ideal) / ideal_step

    assert 0 <= np.max(np.abs(inl)) <= 1
    assert 0 <= np.max(np.abs(dnl)) <= 1

    return inl, dnl


# -----------------------------------------------------------------------------
# cocotb test - combines dynamic + static tests
# -----------------------------------------------------------------------------


@cocotb.test()
async def run_adc_characterisation(dut):
    """Drive coherent sine + ramp, analyse dynamic specs and INL/DNL."""

    await Timer(10, units="ns")

    # ------------------------------------------------------------------ FFT run
    codes_fft = np.empty(N_SAMPLES, dtype=np.int16)
    for n in range(N_SAMPLES):
        t = n / FS
        vin = 0.5 * VREF * (1 + math.sin(2 * math.pi * F_IN * t))
        dut.vin.value = vin
        await Timer(FS_NS, units="ns")
        codes_fft[n] = dut.code.value.integer

    dyn = calc_dynamic_metrics(codes_fft)
    for k in ("SINAD", "ENOB", "SNR", "THD", "SFDR"):
        dut._log.info(f"{k:5s}: {dyn[k]:6.2f}")

    # ---------------------------------------------------------------- spectrum
    spec_pdf = pathlib.Path("flash_adc8_spectrum.pdf")
    plt.figure(figsize=(6.4, 4.8))
    plt.semilogx(dyn["freqs"], 10 * np.log10(np.maximum(dyn["spec"], DB_EPS)))
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Power (dB)")
    plt.title("8-bit Flash ADC - Output Spectrum")
    plt.grid(True, which="both", ls=":")
    plt.tight_layout()
    plt.savefig(spec_pdf, format="pdf")
    plt.close()
    dut._log.info(f"Spectrum saved to {spec_pdf.resolve()}")

    dut.vin.value = 0.0
    await Timer(10, units="us")

    # ------------------------------------------------------------- ramp run
    codes_ramp = np.empty(RAMP_SAMPLES, dtype=np.int16)
    for n in range(RAMP_SAMPLES):
        vin = (n / (RAMP_SAMPLES - 1)) * VREF
        dut.vin.value = vin
        await Timer(FS_NS, units="ns")
        codes_ramp[n] = dut.code.value.integer

    inl, dnl = calc_inl_dnl(codes_ramp)
    dut._log.info(f"Max |INL| = {np.max(np.abs(inl)):.3f} LSB,  Max |DNL| = {np.max(np.abs(dnl)):.3f} LSB")

    # --------------------------------------------------------------- INL/DNL plot
    lin_pdf = pathlib.Path("flash_adc8_inl_dnl.pdf")
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(6.4, 6.4), sharex=True)

    codes = np.arange(256)
    ax0.stem(codes, dnl, basefmt=" ")
    ax0.set_ylabel("DNL [LSB]")
    ax0.grid(True, ls=":")

    ax1.stem(codes, inl, basefmt=" ")
    ax1.set_xlabel("Code")
    ax1.set_ylabel("INL [LSB]")
    ax1.grid(True, ls=":")

    fig.suptitle("8-bit Flash ADC - Static Linearity")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(lin_pdf, format="pdf")
    plt.close()
    dut._log.info(f"INL/DNL plots saved to {lin_pdf.resolve()}")


def test_flash_adc8():
    sim = os.getenv("SIM", "icarus")
    verilog_model = os.getenv("VERILOG_MODEL", None)

    proj_path = pathlib.Path(__file__).resolve().parent

    test_args = []
    extra_env = {}
    defines = {}
    if verilog_model:
        defines = {"VERILOG_MODEL": "1"}
    else:
        test_args = ["-M", spicebind.get_lib_dir(), "-m", "spicebind_vpi"]
        extra_env = {"SPICE_NETLIST": str(proj_path / "flash_adc8.cir"), "HDL_INSTANCE": "flash_adc8"}

    sources = [proj_path / "flash_adc8.v"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="flash_adc8",
        defines=defines,
        always=True,
    )

    runner.test(
        hdl_toplevel="flash_adc8",
        test_module="test_flash_adc8,",
        test_args=test_args,
        extra_env=extra_env,
    )


if __name__ == "__main__":
    test_flash_adc8()
