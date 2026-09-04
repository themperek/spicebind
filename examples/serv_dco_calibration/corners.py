"""Synthetic PVT-like demonstration conditions (not foundry corners)."""

from __future__ import annotations

from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent

# CUNIT/VDD/temp are chosen so co-sim edge counts (400 ns window) straddle
# firmware TARGET=32 at clearly different trim codes.
CORNERS = {
    "nominal": {
        "models": "models_tt.inc",
        "vdd": 3.3,
        "temp": 27,
        "cunit": "90e-15",
        "expected_pass": True,
        "label": "TT / 3.3 V / 27 C",
    },
    "slow": {
        "models": "models_ss.inc",
        "vdd": 3.2,
        "temp": 100,
        "cunit": "100e-15",
        "expected_pass": True,
        "label": "slow / 3.2 V / 100 C",
    },
    "fast": {
        "models": "models_ff.inc",
        "vdd": 3.3,
        "temp": 0,
        "cunit": "70e-15",
        "expected_pass": True,
        "label": "fast / 3.3 V / 0 C",
    },
    "extreme_slow": {
        "models": "models_xx.inc",
        "vdd": 3.0,
        "temp": 125,
        "cunit": "140e-15",
        "expected_pass": False,
        "label": "extreme slow / 3.0 V / 125 C",
    },
}


def render_netlist(dest: Path, corner: dict, tran_step: str = "0.2ns", tran_stop: str = "500us") -> Path:
    template = (EXAMPLE / "spice" / "dco.cir.in").read_text()
    models = (EXAMPLE / "spice" / corner["models"]).resolve()
    text = template.format(
        VDD=corner["vdd"],
        TEMP=corner["temp"],
        MODELS=models,
        CUNIT=corner["cunit"],
        TRAN_STEP=tran_step,
        TRAN_STOP=tran_stop,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    return dest
