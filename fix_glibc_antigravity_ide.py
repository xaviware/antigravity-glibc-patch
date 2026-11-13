#!/usr/bin/env python3
"""
Parche de compatibilidad GLIBC 2.27 (Ubuntu 18.04 / Peppermint 10) para Antigravity IDE.
Reemplaza la referencia a fcntl64@GLIBC_2.28 por fcntl@GLIBC_2.2.5 en:
  - pty.node (terminal integrada)
  - vscode-sqlite3.node (base de datos de estado de VS Code)
"""
import os
import struct
import subprocess
import sys

IDE_ROOT = os.path.expanduser("~/.local/share/antigravity-ide")
TARGETS = [
    os.path.join(IDE_ROOT, "resources/app/node_modules/node-pty/build/Release/pty.node"),
    os.path.join(IDE_ROOT, "resources/app/node_modules/@vscode/sqlite3/build/Release/vscode-sqlite3.node"),
]


def patch_elf(path: str) -> None:
    if not os.path.exists(path):
        print(f"[SKIP] No existe: {path}")
        return

    with open(path, "rb") as f:
        data = bytearray(f.read())

    e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    shstr_off = struct.unpack_from("<Q", data, e_shoff + e_shstrndx * e_shentsize + 0x18)[0]

    sections = {}
    for i in range(e_shnum):
        sh = e_shoff + i * e_shentsize
        name_idx = struct.unpack_from("<I", data, sh)[0]
        end = data.index(0, shstr_off + name_idx)
        name = data[shstr_off + name_idx : end].decode()
        sh_offset, sh_size = struct.unpack_from("<QQ", data, sh + 0x18)
        sections[name] = (sh_offset, sh_size)

    dynstr_off, _ = sections[".dynstr"]
    dynsym_off, dynsym_sz = sections[".dynsym"]
    gnuver_off, _ = sections[".gnu.version"]
    verr_off, _ = sections[".gnu.version_r"]

    patched = False
    nsyms = dynsym_sz // 24
    for sym_idx in range(nsyms):
        st_name = struct.unpack_from("<I", data, dynsym_off + sym_idx * 24)[0]
        if data[dynstr_off + st_name : dynstr_off + st_name + 8] == b"fcntl64\x00":
            data[dynstr_off + st_name : dynstr_off + st_name + 8] = b"fcntl\x00\x00\x00"
            struct.pack_into("<H", data, gnuver_off + sym_idx * 2, 4)
            patched = True

    vn_version, vn_cnt, vn_file, vn_aux, vn_next = struct.unpack_from("<HHIII", data, verr_off + 0x40)
    if vn_cnt == 3 and vn_aux == 16:
        struct.pack_into("<HHIII", data, verr_off + 0x40, vn_version, 2, vn_file, 32, vn_next)
        patched = True

    if patched:
        with open(path, "wb") as f:
            f.write(data)
        print(f"[OK] Parcheado: {path}")
    else:
        print(f"[OK] Ya estaba parcheado: {path}")

    out = subprocess.check_output(["ldd", "-r", path], stderr=subprocess.STDOUT).decode()
    bad = [line for line in out.splitlines() if "not found" in line or "GLIBC_2.28" in line]
    if bad:
        print(f"[WARN] Problemas restantes en {path}:\n  " + "\n  ".join(bad))
        sys.exit(1)


if __name__ == "__main__":
    for target in TARGETS:
        patch_elf(target)
