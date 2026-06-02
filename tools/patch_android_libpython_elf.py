"""Patch Flet Android libpython ELF segment offsets.

Some Flet/serious_python Android Python runtime archives contain a final
PT_LOAD segment whose file offset is not congruent with its virtual address.
Android's dynamic linker can then read the dynamic section from the wrong file
position and report a missing DT_GNU_HASH. This tool inserts file padding before
misaligned load segments and updates file offsets while keeping virtual
addresses unchanged.
"""

from __future__ import annotations

import argparse
import shutil
import struct
from pathlib import Path

PT_LOAD = 1
SHT_NOBITS = 8


class ElfError(RuntimeError):
    pass


def _read_u16(data: bytearray, offset: int, endian: str) -> int:
    return struct.unpack_from(f"{endian}H", data, offset)[0]


def _read_u32(data: bytearray, offset: int, endian: str) -> int:
    return struct.unpack_from(f"{endian}I", data, offset)[0]


def _read_u64(data: bytearray, offset: int, endian: str) -> int:
    return struct.unpack_from(f"{endian}Q", data, offset)[0]


def _write_u32(data: bytearray, offset: int, value: int, endian: str) -> None:
    struct.pack_into(f"{endian}I", data, offset, value)


def _write_u64(data: bytearray, offset: int, value: int, endian: str) -> None:
    struct.pack_into(f"{endian}Q", data, offset, value)


def _ceil_to_matching_mod(offset: int, align: int, target_mod: int) -> int:
    delta = (target_mod - (offset % align)) % align
    return offset + delta


def _parse_header(data: bytearray) -> dict[str, int | str]:
    if data[:4] != b"\x7fELF":
        raise ElfError("not an ELF file")
    elf_class = data[4]
    if elf_class not in (1, 2):
        raise ElfError(f"unsupported ELF class: {elf_class}")
    endian_id = data[5]
    if endian_id == 1:
        endian = "<"
    elif endian_id == 2:
        endian = ">"
    else:
        raise ElfError(f"unsupported ELF endian id: {endian_id}")

    if elf_class == 2:
        return {
            "class": elf_class,
            "endian": endian,
            "e_phoff": _read_u64(data, 32, endian),
            "e_shoff": _read_u64(data, 40, endian),
            "e_phentsize": _read_u16(data, 54, endian),
            "e_phnum": _read_u16(data, 56, endian),
            "e_shentsize": _read_u16(data, 58, endian),
            "e_shnum": _read_u16(data, 60, endian),
        }

    return {
        "class": elf_class,
        "endian": endian,
        "e_phoff": _read_u32(data, 28, endian),
        "e_shoff": _read_u32(data, 32, endian),
        "e_phentsize": _read_u16(data, 42, endian),
        "e_phnum": _read_u16(data, 44, endian),
        "e_shentsize": _read_u16(data, 46, endian),
        "e_shnum": _read_u16(data, 48, endian),
    }


def _program_offset_field(elf_class: int) -> int:
    return 8 if elf_class == 2 else 4


def _program_vaddr_field(elf_class: int) -> int:
    return 16 if elf_class == 2 else 8


def _program_align_field(elf_class: int) -> int:
    return 48 if elf_class == 2 else 28


def _section_offset_field(elf_class: int) -> int:
    return 24 if elf_class == 2 else 16


def _header_shoff_field(elf_class: int) -> int:
    return 40 if elf_class == 2 else 32


def _header_phoff_field(elf_class: int) -> int:
    return 32 if elf_class == 2 else 28


def _read_word(data: bytearray, offset: int, elf_class: int, endian: str) -> int:
    if elf_class == 2:
        return _read_u64(data, offset, endian)
    return _read_u32(data, offset, endian)


def _write_word(data: bytearray, offset: int, value: int, elf_class: int, endian: str) -> None:
    if elf_class == 2:
        _write_u64(data, offset, value, endian)
    else:
        _write_u32(data, offset, value, endian)


def _load_segments(data: bytearray, header: dict[str, int | str]) -> list[dict[str, int]]:
    elf_class = int(header["class"])
    endian = str(header["endian"])
    phoff = int(header["e_phoff"])
    phentsize = int(header["e_phentsize"])
    phnum = int(header["e_phnum"])
    segments: list[dict[str, int]] = []
    for index in range(phnum):
        base = phoff + index * phentsize
        p_type = _read_u32(data, base, endian)
        if p_type != PT_LOAD:
            continue
        p_offset = _read_word(data, base + _program_offset_field(elf_class), elf_class, endian)
        p_vaddr = _read_word(data, base + _program_vaddr_field(elf_class), elf_class, endian)
        p_align = _read_word(data, base + _program_align_field(elf_class), elf_class, endian)
        segments.append(
            {
                "index": index,
                "base": base,
                "offset": p_offset,
                "vaddr": p_vaddr,
                "align": p_align,
            }
        )
    return segments


def _insert_padding_and_shift_offsets(data: bytearray, insert_at: int, pad: int) -> None:
    header = _parse_header(data)
    elf_class = int(header["class"])
    endian = str(header["endian"])

    data[insert_at:insert_at] = b"\0" * pad

    phoff = int(header["e_phoff"])
    if phoff >= insert_at:
        _write_word(data, _header_phoff_field(elf_class), phoff + pad, elf_class, endian)

    e_shoff = int(header["e_shoff"])
    if e_shoff >= insert_at:
        _write_word(data, _header_shoff_field(elf_class), e_shoff + pad, elf_class, endian)

    phentsize = int(header["e_phentsize"])
    phnum = int(header["e_phnum"])
    for index in range(phnum):
        base = phoff + index * phentsize
        field = base + _program_offset_field(elf_class)
        p_offset = _read_word(data, field, elf_class, endian)
        if p_offset >= insert_at:
            _write_word(data, field, p_offset + pad, elf_class, endian)

    header = _parse_header(data)
    shoff = int(header["e_shoff"])
    shentsize = int(header["e_shentsize"])
    shnum = int(header["e_shnum"])
    for index in range(shnum):
        base = shoff + index * shentsize
        sh_type = _read_u32(data, base + 4, endian)
        if sh_type == SHT_NOBITS:
            continue
        field = base + _section_offset_field(elf_class)
        sh_offset = _read_word(data, field, elf_class, endian)
        if sh_offset >= insert_at:
            _write_word(data, field, sh_offset + pad, elf_class, endian)


def patch_elf(path: Path, backup: bool = True) -> list[str]:
    data = bytearray(path.read_bytes())
    changes: list[str] = []

    while True:
        header = _parse_header(data)
        misaligned = None
        for segment in _load_segments(data, header):
            align = segment["align"]
            if align <= 1:
                continue
            if (segment["offset"] - segment["vaddr"]) % align != 0:
                misaligned = segment
                break
        if misaligned is None:
            break

        align = misaligned["align"]
        desired_offset = _ceil_to_matching_mod(
            misaligned["offset"], align, misaligned["vaddr"] % align
        )
        pad = desired_offset - misaligned["offset"]
        if pad <= 0:
            raise ElfError(f"could not compute positive padding for {path}")
        changes.append(
            "PT_LOAD#{index}: offset 0x{offset:x} -> 0x{desired:x}, "
            "vaddr 0x{vaddr:x}, align 0x{align:x}, pad {pad}".format(
                index=misaligned["index"],
                offset=misaligned["offset"],
                desired=desired_offset,
                vaddr=misaligned["vaddr"],
                align=align,
                pad=pad,
            )
        )
        _insert_padding_and_shift_offsets(data, misaligned["offset"], pad)

    if changes:
        if backup:
            backup_path = path.with_suffix(path.suffix + ".bak")
            if not backup_path.exists():
                shutil.copy2(path, backup_path)
        path.write_bytes(data)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    for path in args.paths:
        changes = patch_elf(path, backup=not args.no_backup)
        if changes:
            print(f"patched {path}")
            for change in changes:
                print(f"  {change}")
        else:
            print(f"already aligned {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
