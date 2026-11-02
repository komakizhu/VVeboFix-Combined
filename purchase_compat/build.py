#!/usr/bin/env python3
"""Compile VVebo purchase compatibility and build a RootHide deb / sideload IPA."""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path, PurePosixPath
import plistlib
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from build_package import ar_member, tar_gz

VERSION = "0.1.1"
PACKAGE = "com.local.vvebo.purchasecompat"
APP_ID = "com.johnil.vvebo"
APP_UUID = "595ED4FF-9558-308B-93C6-33EB09125340"
LIBRARY = "VVeboPurchaseCompat.dylib"
BUILD = ROOT / "build/purchase-compat"
DIST = ROOT / "dist/purchase-compat"


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args!r}\n{result.stdout}{result.stderr}")
    return result.stdout + result.stderr


def metadata(data: bytes) -> dict:
    if data[:4] != b"\xcf\xfa\xed\xfe":
        raise ValueError("Expected the supplied thin arm64 Mach-O")
    result = {"sections": {}, "dependencies": []}
    count, command_bytes = struct.unpack_from("<II", data, 16)
    result["command_end"] = 32 + command_bytes
    offset = 32
    for _ in range(count):
        command, size = struct.unpack_from("<II", data, offset)
        if size < 8 or offset + size > len(data):
            raise ValueError("Malformed Mach-O load commands")
        if command == 0x1B:
            result["uuid"] = str(uuid.UUID(bytes=data[offset + 8 : offset + 24])).upper()
        elif command == 0x1D:
            result["signature"] = struct.unpack_from("<II", data, offset + 8)
        elif command == 0x2C:
            result["cryptid"] = struct.unpack_from("<I", data, offset + 16)[0]
        elif command == 0xC:
            name = struct.unpack_from("<I", data, offset + 8)[0]
            result["dependencies"].append(data[offset + name : offset + size].split(b"\0", 1)[0].decode())
        elif command == 0x19:
            for index in range(struct.unpack_from("<I", data, offset + 64)[0]):
                section = offset + 72 + 80 * index
                name = data[section : section + 16].split(b"\0", 1)[0].decode()
                segment = data[section + 16 : section + 32].split(b"\0", 1)[0].decode()
                length = struct.unpack_from("<Q", data, section + 40)[0]
                position = struct.unpack_from("<I", data, section + 48)[0]
                result["sections"][(segment, name)] = (position, length)
        offset += size
    return result


def entitlements(data: bytes, info: dict) -> dict:
    signature, _ = info["signature"]
    magic, _, count = struct.unpack_from(">III", data, signature)
    if magic != 0xFADE0CC0:
        raise ValueError("Unexpected original signature container")
    for index in range(count):
        kind, offset = struct.unpack_from(">II", data, signature + 12 + index * 8)
        if kind == 5:
            start = signature + offset
            magic, length = struct.unpack_from(">II", data, start)
            if magic != 0xFADE7171:
                raise ValueError("Unexpected entitlement blob")
            return plistlib.loads(data[start + 8 : start + length])
    raise ValueError("Original app entitlements are missing; refusing to discard them")


def add_library(data: bytes) -> bytes:
    info = metadata(data)
    if info.get("uuid") != APP_UUID or info.get("cryptid") != 0:
        raise ValueError("Expected the decrypted full-permissions VVebo 3.3.31 build 4")
    name = "@executable_path/Frameworks/" + LIBRARY
    if name in info["dependencies"]:
        raise ValueError("Source IPA already contains this compatibility library")
    text_offset, _ = info["sections"][("__TEXT", "__text")]
    encoded = name.encode() + b"\0"
    size = (24 + len(encoded) + 7) & ~7
    start = info["command_end"]
    if start + size > text_offset or any(data[start : start + size]):
        raise ValueError("Insufficient unused load-command padding")
    command = struct.pack("<6I", 0xC, size, 24, 0, 0, 0) + encoded
    result = bytearray(data)
    result[start : start + size] = command.ljust(size, b"\0")
    count, command_bytes = struct.unpack_from("<II", data, 16)
    struct.pack_into("<II", result, 16, count + 1, command_bytes + size)
    return bytes(result)


def check_text_unchanged(before: bytes, after: bytes) -> None:
    old, new = metadata(before), metadata(after)
    for key, (offset, size) in old["sections"].items():
        if key[0] != "__TEXT":
            continue
        other_offset, other_size = new["sections"][key]
        if size != other_size or before[offset : offset + size] != after[other_offset : other_offset + other_size]:
            raise ValueError(f"Original App section changed: {key}")


def build_library() -> Path:
    BUILD.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)
    source = ROOT / "purchase_compat/VVeboPurchaseCompat.m"
    test = BUILD / "test-compat"
    run("xcrun", "clang", "-fobjc-arc", "-Wall", "-Wextra", "-Werror",
        "-DVV_COMPAT_TESTING=1", "-framework", "Foundation", str(source),
        str(ROOT / "purchase_compat/test_compat.m"), "-o", str(test))
    print(run(str(test), "--startup"))
    print(run(str(test)))
    sdk = run("xcrun", "--sdk", "iphoneos", "--show-sdk-path").strip()
    target = BUILD / LIBRARY
    run("xcrun", "clang", "-target", "arm64-apple-ios14.0", "-isysroot", sdk,
        "-dynamiclib", "-fobjc-arc", "-Wall", "-Wextra", "-Werror",
        "-DVV_COMPAT_TESTING=0", "-framework", "Foundation",
        "-Wl,-install_name,@rpath/" + LIBRARY, "-Wl,-current_version," + VERSION,
        "-Wl,-compatibility_version," + VERSION, str(source), "-o", str(target))
    run("codesign", "--force", "--sign", "-", "--timestamp=none", str(target))
    run("codesign", "--verify", "--strict", str(target))
    return target


def build_deb(library: Path) -> Path:
    base = "Library/MobileSubstrate/DynamicLibraries/"
    files = {
        base + LIBRARY: (library.read_bytes(), 0o755),
        base + "VVeboPurchaseCompat.plist": (
            plistlib.dumps({"Filter": {"Bundles": [APP_ID]}}), 0o644),
        "usr/share/doc/" + PACKAGE + "/README.zh-CN.md": (
            (ROOT / "purchase_compat/README.md").read_bytes(), 0o644),
    }
    control = (
        f"Package: {PACKAGE}\nName: VVebo 已购兼容 (RootHide)\nVersion: {VERSION}\n"
        "Architecture: iphoneos-arm64e\nSection: Tweaks\nPriority: optional\n"
        "Maintainer: Local Compatibility Build\n"
        "Depends: firmware (>= 15.0), mobilesubstrate\n"
        "Description: Local purchased-feature compatibility for VVebo 3.3.31\n"
        " Applies only to the app's local MMKV license-expiry reader.\n"
        " Actual iCloud synchronization requires device testing.\n"
    ).encode()
    sums = "".join(f"{hashlib.md5(value[0]).hexdigest()}  {name}\n"
                   for name, value in sorted(files.items())).encode()
    timestamp = int((ROOT / "purchase_compat/VVeboPurchaseCompat.m").stat().st_mtime)
    members = {"debian-binary": b"2.0\n",
               "control.tar.gz": tar_gz({"control": (control, 0o644), "md5sums": (sums, 0o644)}, timestamp),
               "data.tar.gz": tar_gz(files, timestamp)}
    target = DIST / f"{PACKAGE}_{VERSION}_iphoneos-arm64e.deb"
    target.write_bytes(b"!<arch>\n" + b"".join(ar_member(k, v, timestamp) for k, v in members.items()))
    return target


def build_ipa(source: Path, library: Path) -> Path:
    work = Path(tempfile.mkdtemp(prefix="ipa-", dir=BUILD))
    with zipfile.ZipFile(source) as archive:
        for item in archive.infolist():
            relative = PurePosixPath(item.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe ZIP path")
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("Unexpected symlink in the source IPA")
            target = work / item.filename
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(item))
                target.chmod(mode & 0o777 or 0o644)
    apps = list((work / "Payload").glob("*.app"))
    if len(apps) != 1:
        raise ValueError("Expected a single VVebo app")
    app = apps[0]
    info = plistlib.loads((app / "Info.plist").read_bytes())
    if (info.get("CFBundleIdentifier"), info.get("CFBundleShortVersionString"),
            str(info.get("CFBundleVersion"))) != (APP_ID, "3.3.31", "4"):
        raise ValueError("Unexpected App identity or version")
    executable = app / info["CFBundleExecutable"]
    original = executable.read_bytes()
    original_entitlements = entitlements(original, metadata(original))
    if "iCloud.com.johnil.vvebo" not in original_entitlements.get("com.apple.developer.icloud-container-identifiers", []):
        raise ValueError("Original iCloud container entitlement is missing")
    entitlement_file = work / "app-entitlements.plist"
    entitlement_file.write_bytes(plistlib.dumps(original_entitlements))
    executable.write_bytes(add_library(original))
    executable.chmod(0o755)
    framework_dir = app / "Frameworks"
    shutil.copyfile(library, framework_dir / LIBRARY)
    (framework_dir / LIBRARY).chmod(0o755)
    for framework in sorted(framework_dir.glob("*.framework")):
        run("codesign", "--force", "--sign", "-", "--timestamp=none", str(framework))
    for dynamic_library in framework_dir.glob("*.dylib"):
        run("codesign", "--force", "--sign", "-", "--timestamp=none", str(dynamic_library))
    run("codesign", "--force", "--sign", "-", "--timestamp=none", "--entitlements",
        str(entitlement_file), str(app))
    run("codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app))
    final = executable.read_bytes()
    check_text_unchanged(original, final)
    if entitlements(final, metadata(final)) != original_entitlements:
        raise ValueError("App entitlements changed")
    if plistlib.loads((app / "Info.plist").read_bytes()) != info:
        raise ValueError("App identity changed")
    if "@executable_path/Frameworks/" + LIBRARY not in metadata(final)["dependencies"]:
        raise ValueError("Compatibility library is not loaded")
    target = DIST / f"VVebo_3.3.31_PurchaseCompat_{VERSION}.ipa"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted((work / "Payload").rglob("*")):
            archive.write(path, path.relative_to(work).as_posix())
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError("Repacked IPA failed ZIP validation")
        if archive.read("Payload/" + app.name + "/" + info["CFBundleExecutable"]) != final:
            raise ValueError("IPA executable differs from verified app")
    print("Existing App __TEXT sections unchanged; identity and original iCloud/App Group entitlements preserved.")
    print("Entire App and nested frameworks passed codesign --verify --deep --strict.")
    print("Verified app staging directory:", app)
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ipa", type=Path, help="Original full-permissions VVebo 3.3.31 IPA")
    args = parser.parse_args()
    library = build_library()
    print("RootHide deb:", build_deb(library))
    if args.ipa:
        print("Patched IPA:", build_ipa(args.ipa, library))
    print("Device UI, theme changes and actual iCloud sync: not tested on this computer.")


if __name__ == "__main__":
    main()
