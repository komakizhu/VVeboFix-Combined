#!/usr/bin/env python3
"""Build the supplied VVeboFix binary as a native RootHide deb on macOS."""

from __future__ import annotations

import gzip
import hashlib
import io
import math
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parent
PACKAGE = "com.lhl.vvebofix"
VERSION = "1.0.1"
ARCHITECTURE = "iphoneos-arm64e"
APPLICATION = "com.johnil.vvebo"
DYLIB_DIR = "Library/MobileSubstrate/DynamicLibraries"


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed ({result.returncode}): {result.stdout}{result.stderr}")
    return result.stdout + result.stderr


def macho(path: Path) -> dict:
    data = path.read_bytes()
    magic, cpu, subtype, kind, count, *_ = struct.unpack_from("<8I", data)
    if (magic, cpu, subtype & 0xFFFFFF, kind) != (0xFEEDFACF, 0x100000C, 2, 6):
        raise ValueError("Expected the supplied thin arm64e Mach-O dylib")
    result = {"rpaths": [], "dependencies": [], "sections": {}}
    offset = 32
    for _ in range(count):
        command, length = struct.unpack_from("<II", data, offset)
        if length < 8 or offset + length > len(data):
            raise ValueError("Invalid Mach-O load command")
        if command in (0x8000001C, 0xC, 0x80000018, 0x8000001F):
            name_offset = struct.unpack_from("<I", data, offset + 8)[0]
            name = data[offset + name_offset : offset + length].split(b"\0", 1)[0].decode()
            field = "rpaths" if command == 0x8000001C else "dependencies"
            result[field].append(name)
        elif command == 0x19:
            number_of_sections = struct.unpack_from("<I", data, offset + 64)[0]
            for index in range(number_of_sections):
                section = offset + 72 + index * 80
                name = data[section : section + 16].split(b"\0", 1)[0].decode()
                segment = data[section + 16 : section + 32].split(b"\0", 1)[0].decode()
                size = struct.unpack_from("<Q", data, section + 40)[0]
                file_offset = struct.unpack_from("<I", data, section + 48)[0]
                if segment == "__TEXT":
                    result["sections"][(segment, name)] = data[file_offset : file_offset + size]
        offset += length
    return result


def tar_gz(files: dict[str, tuple[bytes, int]], timestamp: int) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        directories = {"."}
        for name in files:
            parent = Path(name).parent
            while parent != Path("."):
                directories.add(parent.as_posix())
                parent = parent.parent
        for name in sorted(directories, key=lambda item: (item.count("/"), item)):
            entry = tarfile.TarInfo("." if name == "." else "./" + name)
            entry.type = tarfile.DIRTYPE
            entry.mode = 0o755
            entry.uid = entry.gid = 0
            entry.uname = entry.gname = "root"
            entry.mtime = timestamp
            archive.addfile(entry)
        for name, (contents, mode) in sorted(files.items()):
            entry = tarfile.TarInfo("./" + name)
            entry.size = len(contents)
            entry.mode = mode
            entry.uid = entry.gid = 0
            entry.uname = entry.gname = "root"
            entry.mtime = timestamp
            archive.addfile(entry, io.BytesIO(contents))
    return gzip.compress(stream.getvalue(), compresslevel=9, mtime=timestamp)


def ar_member(name: str, contents: bytes, timestamp: int) -> bytes:
    header = (
        f"{name:<16}{timestamp:<12}{0:<6}{0:<6}"
        f"{'100644':<8}{len(contents):<10}`\n"
    ).encode("ascii")
    if len(header) != 60:
        raise ValueError("Invalid ar member header")
    return header + contents + (b"\n" if len(contents) % 2 else b"")


def main() -> None:
    source = ROOT / "input/VVeboFix.original.dylib"
    original = macho(source)
    timestamp = int(source.stat().st_mtime)
    build = ROOT / "build"
    output = ROOT / "dist"
    build.mkdir(exist_ok=True)
    output.mkdir(exist_ok=True)
    library = build / "VVeboFix.dylib"
    shutil.copyfile(source, library)
    library.chmod(0o755)

    # Normalize the special signature first. Removing it alone leaves alignment
    # padding in __LINKEDIT that Apple's install_name_tool refuses to process.
    # Sign again below after changing the load commands.
    run("codesign", "--force", "--sign", "-", "--timestamp=none", str(library))
    paths = set(original["rpaths"])
    for old in original["rpaths"]:
        if old.startswith("/var/jb/"):
            new = "@loader_path/.jbroot/" + old[len("/var/jb/") :]
            operation = ("-delete_rpath", old) if new in paths else ("-rpath", old, new)
            run("xcrun", "install_name_tool", *operation, str(library))
            paths.discard(old)
            paths.add(new)
    for old in original["dependencies"]:
        if old.startswith("/var/jb/"):
            new = "@loader_path/.jbroot/" + old[len("/var/jb/") :]
            run("xcrun", "install_name_tool", "-change", old, new, str(library))
    run("codesign", "--force", "--sign", "-", "--timestamp=none", str(library))
    verification = run("codesign", "--verify", "--strict", "--verbose=2", str(library))
    signature = run("codesign", "--display", "--verbose=4", str(library))
    converted = macho(library)
    if converted["sections"] != original["sections"]:
        raise ValueError("Conversion changed a __TEXT section")
    if any(name.startswith("/var/jb") for name in converted["rpaths"] + converted["dependencies"]):
        raise ValueError("A rootless absolute load path remains")
    if "Signature=adhoc" not in signature or "TeamIdentifier=not set" not in signature:
        raise ValueError("Expected ad-hoc signing without a certificate team")

    loader = plistlib.dumps({"Filter": {"Bundles": [APPLICATION]}}, sort_keys=True)
    files = {
        f"{DYLIB_DIR}/VVeboFix.dylib": (library.read_bytes(), 0o755),
        f"{DYLIB_DIR}/VVeboFix.plist": (loader, 0o644),
        f"usr/share/doc/{PACKAGE}/README.zh-CN.txt": ((ROOT / "INSTALL.zh-CN.txt").read_bytes(), 0o644),
    }
    installed_size = sum(math.ceil(len(contents) / 1024) for contents, _ in files.values())
    control = (
        f"Package: {PACKAGE}\nName: VVeboFix (RootHide)\nVersion: {VERSION}\n"
        f"Architecture: {ARCHITECTURE}\nInstalled-Size: {installed_size}\n"
        "Section: Tweaks\nPriority: optional\nMaintainer: Local RootHide Conversion\n"
        "Depends: firmware (>= 15.0), mobilesubstrate\n"
        "Homepage: https://github.com/nildeveloper/VVeboFix\n"
        "Description: VVebo timeline and fans fix for Relaxin / RootHide\n"
        " Local conversion of the supplied VVeboFix library.\n"
        f" Loads only in {APPLICATION}. Device runtime testing is required.\n"
    ).encode()
    sums = "".join(
        f"{hashlib.md5(contents).hexdigest()}  {name}\n"
        for name, (contents, _) in sorted(files.items())
    ).encode()
    controls = {"control": (control, 0o644), "md5sums": (sums, 0o644)}
    members = {
        "debian-binary": b"2.0\n",
        "control.tar.gz": tar_gz(controls, timestamp),
        "data.tar.gz": tar_gz(files, timestamp),
    }
    package = output / f"{PACKAGE}_{VERSION}_{ARCHITECTURE}.deb"
    package.write_bytes(b"!<arch>\n" + b"".join(ar_member(k, v, timestamp) for k, v in members.items()))
    package.chmod(0o644)
    (build / "control").write_bytes(control)
    (build / "VVeboFix.plist").write_bytes(loader)
    (build / "codesign-verification.txt").write_text(verification + "\n" + signature)
    print(f"Built: {package}")
    print(f"Size: {package.stat().st_size} bytes")
    print("All __TEXT sections unchanged; ad-hoc signature verified.")
    print("RootHide rpaths:", converted["rpaths"])
    print("Runtime on iPhone: not tested.")


if __name__ == "__main__":
    main()
