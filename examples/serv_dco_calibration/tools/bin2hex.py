#!/usr/bin/env python3
"""Convert a little-endian RV32 binary to $readmemh word hex."""

from __future__ import annotations

import struct
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        sys.stderr.write("usage: bin2hex.py firmware.bin firmware.hex\n")
        sys.exit(2)
    data = Path(sys.argv[1]).read_bytes()
    if len(data) % 4:
        data += b"\x00" * (4 - (len(data) % 4))
    words = list(struct.unpack("<" + "I" * (len(data) // 4), data))
    # Pad so $readmemh fills a 2 Ki-word RAM without an Icarus warning.
    words.extend([0] * max(0, 2048 - len(words)))
    Path(sys.argv[2]).write_text(
        "// Generated firmware image. Do not edit.\n"
        + "".join(f"{w:08x}\n" for w in words)
    )


if __name__ == "__main__":
    main()
