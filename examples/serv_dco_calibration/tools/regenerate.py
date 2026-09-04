#!/usr/bin/env python3
"""Regenerate committed SERV RTL and firmware artifacts.

Normal pytest does not call this. Docker/Podman is only required when a
RISC-V GCC is not already on PATH
(https://github.com/iic-jku/IIC-OSIC-TOOLS).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1]
REPO = EXAMPLE.parents[1]
SERV_REPO = "https://github.com/olofk/serv"
SERV_COMMIT = "f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8"
# https://github.com/iic-jku/IIC-OSIC-TOOLS
IIC_IMAGE = "docker.io/hpretl/iic-osic-tools:2026.07"

# Files actually elaborated for width=1, no C, no CSR, no MDU, no debug.
# Unused optional modules are omitted so Icarus does not have to parse them.
SERV_FILES = [
    "servile/servile.v",
    "servile/servile_mux.v",
    "servile/servile_arbiter.v",
    "rtl/serv_bufreg.v",
    "rtl/serv_bufreg2.v",
    "rtl/serv_alu.v",
    "rtl/serv_csr.v",
    "rtl/serv_ctrl.v",
    "rtl/serv_decode.v",
    "rtl/serv_immdec.v",
    "rtl/serv_mem_if.v",
    "rtl/serv_rf_if.v",
    "rtl/serv_rf_ram_if.v",
    "rtl/serv_rf_ram.v",
    "rtl/serv_state.v",
    "rtl/serv_top.v",
]


def run(cmd, **kwargs):
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, **kwargs)


def find_container() -> str | None:
    for name in ("podman", "docker"):
        if shutil.which(name):
            return name
    return None


def find_riscv_make_vars() -> dict[str, str]:
    prefixes = [
        os.environ.get("RISCV_PREFIX", ""),
        "riscv64-unknown-elf-",
        "riscv32-unknown-elf-",
        "riscv-none-elf-",
        "riscv32-unknown-linux-gnu-",
    ]
    for prefix in prefixes:
        if prefix and shutil.which(prefix + "gcc"):
            return {"PREFIX": prefix}
    return {}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def fetch_serv(dest: Path) -> None:
    if dest.exists() and (dest / ".git").exists():
        try:
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=dest, text=True
            ).strip()
        except subprocess.CalledProcessError:
            head = ""
        if head == SERV_COMMIT:
            return
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    run(["git", "init"], cwd=dest)
    run(["git", "remote", "add", "origin", SERV_REPO], cwd=dest)
    run(["git", "fetch", "--depth", "1", "origin", SERV_COMMIT], cwd=dest)
    run(["git", "checkout", "FETCH_HEAD"], cwd=dest)


def write_serv_rtl(serv_root: Path, out_v: Path, copy_rf: bool = True) -> None:
    chunks = [
        "/*\n",
        " * Generated file. Do not edit.\n",
        f" * Source: {SERV_REPO}\n",
        f" * Commit: {SERV_COMMIT}\n",
        " * CPU core: ISC license. servile wrapper: Apache-2.0.\n",
        " */\n\n",
        "`timescale 1ns / 1ps\n",
    ]
    for rel in SERV_FILES:
        src = serv_root / rel
        chunks.append(f"\n// ---- {rel} ----\n")
        chunks.append(src.read_text())
        if not chunks[-1].endswith("\n"):
            chunks.append("\n")
    chunks.append("\n`default_nettype wire\n")
    out_v.parent.mkdir(parents=True, exist_ok=True)
    out_v.write_text("".join(chunks))
    if copy_rf:
        shutil.copyfile(serv_root / "rtl" / "serv_rf_ram.v", EXAMPLE / "rtl" / "serv_rf_ram.v")


def compile_firmware(out_dir: Path, make_env: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    if make_env:
        env.update(make_env)
    out_dir.mkdir(parents=True, exist_ok=True)
    run(
        ["make", "-C", str(EXAMPLE / "fw"), "all", f"OUT={out_dir}"],
        env=env,
    )


def write_manifest(out_dir: Path) -> None:
    hex_path = out_dir / "firmware.hex"
    rtl_path = out_dir / "serv_rtl.v"
    manifest = {
        "generated": True,
        "do_not_edit": True,
        "serv_repository": SERV_REPO,
        "serv_commit": SERV_COMMIT,
        "iic_osic_tools_image": IIC_IMAGE,
        "march": "rv32i",
        "mabi": "ilp32",
        "serv_width": 1,
        "firmware_hex_sha256": sha256(hex_path) if hex_path.exists() else None,
        "serv_rtl_sha256": sha256(rtl_path) if rtl_path.exists() else None,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def regenerate_in_container(out_dir: Path) -> None:
    engine = find_container()
    if not engine:
        raise SystemExit("No RISC-V GCC on PATH and neither podman nor docker is available")
    work = "/work"
    repo = REPO.resolve()
    out_dir = out_dir.resolve()
    cmd = [engine, "run", "--rm", "-v", f"{repo}:{work}", "-w", work]
    try:
        rel = out_dir.relative_to(repo)
        out_arg = f"{work}/{rel.as_posix()}"
    except ValueError:
        cmd += ["-v", f"{out_dir}:/asset-out"]
        out_arg = "/asset-out"
    script = f"""
set -euo pipefail
export PATH="/foss/tools/riscv-gnu-toolchain/bin:/opt/riscv/bin:$PATH"
if command -v riscv64-unknown-elf-gcc >/dev/null; then
  export RISCV_PREFIX=riscv64-unknown-elf-
elif command -v riscv-none-elf-gcc >/dev/null; then
  export RISCV_PREFIX=riscv-none-elf-
elif command -v riscv32-unknown-elf-gcc >/dev/null; then
  export RISCV_PREFIX=riscv32-unknown-elf-
else
  echo "RISC-V GCC not found in IIC-OSIC-TOOLS image" >&2
  exit 1
fi
python3 {work}/examples/serv_dco_calibration/tools/regenerate.py --in-container --output {out_arg}
"""
    cmd += [IIC_IMAGE, "bash", "-lc", script]
    run(cmd)


ASSET_FILES = ("firmware.hex", "firmware.lst", "serv_rtl.v", "manifest.json")


def do_regenerate(out_dir: Path, make_vars: dict[str, str]) -> None:
    cache = Path(os.environ.get("SERV_CACHE", "/tmp/spicebind-serv"))
    fetch_serv(cache)
    copy_rf = out_dir.resolve() == (EXAMPLE / "generated").resolve()
    write_serv_rtl(cache, out_dir / "serv_rtl.v", copy_rf=copy_rf)
    compile_firmware(out_dir, make_vars)
    write_manifest(out_dir)
    print(f"Wrote artifacts in {out_dir}")


def check_assets(generated: Path, committed: Path) -> None:
    mismatches = []
    for name in ASSET_FILES:
        a = committed / name
        b = generated / name
        if not a.exists() or not b.exists():
            mismatches.append(f"{name}: missing committed={a.exists()} generated={b.exists()}")
            continue
        if a.read_bytes() != b.read_bytes():
            mismatches.append(f"{name}: content differs")
    if mismatches:
        raise SystemExit("Asset check failed:\n  " + "\n  ".join(mismatches))
    print(f"Assets match {committed}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=EXAMPLE / "generated")
    parser.add_argument("--in-container", action="store_true")
    parser.add_argument("--force-container", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Regenerate into a temp directory and compare with --output (committed) files",
    )
    args = parser.parse_args()
    out_dir = args.output.resolve()

    make_vars = find_riscv_make_vars()
    if args.check:
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="spicebind-serv-assets-"))
        try:
            if args.force_container or not make_vars:
                regenerate_in_container(tmp)
            else:
                do_regenerate(tmp, make_vars)
            check_assets(tmp, out_dir)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return

    if args.force_container and not args.in_container:
        regenerate_in_container(out_dir)
        return

    if not make_vars and not args.in_container:
        regenerate_in_container(out_dir)
        return

    do_regenerate(out_dir, make_vars)


if __name__ == "__main__":
    sys.exit(main())
