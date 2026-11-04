#!/usr/bin/env python3
"""Build the XHS startup-feed refresh blocker for every supported injector."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
import plistlib
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
VERSION = "0.1.0"
PACKAGE = "com.local.xhs.norefresh"
DISPLAY_NAME = "小红书防自动刷新"
LIBRARY = "XHSNoRefresh.dylib"
BUILD = ROOT / "build/xhs-no-refresh"
DIST = ROOT / "dist/xhs-no-refresh"


@dataclass(frozen=True)
class Variant:
    """One package layout and its user-visible artifact suffix."""

    suffix: str
    package_version: str
    architecture: str
    data_prefix: str
    label: str


VARIANTS = (
    Variant("rootful", f"{VERSION}+1-rootful", "iphoneos-arm", "", "Rootful"),
    Variant("rootless", f"{VERSION}+1-rootless", "iphoneos-arm64", "var/jb", "Rootless"),
    Variant("roothide", f"{VERSION}+1-roothide", "iphoneos-arm64e", "", "RootHide"),
)
TROLLSTORE_ARTIFACT = f"{DISPLAY_NAME}-{VERSION}-1-trollstore.dylib"


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args!r}\n"
                           f"{result.stdout}{result.stderr}")
    return result.stdout + result.stderr


def tar_gz(files: dict[str, tuple[bytes, int]]) -> bytes:
    import gzip
    import io
    import tarfile

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
            entry.mtime = 0
            archive.addfile(entry)
        for name, (contents, mode) in sorted(files.items()):
            entry = tarfile.TarInfo("./" + name)
            entry.size = len(contents)
            entry.mode = mode
            entry.uid = entry.gid = 0
            entry.uname = entry.gname = "root"
            entry.mtime = 0
            archive.addfile(entry, io.BytesIO(contents))
    return gzip.compress(stream.getvalue(), compresslevel=9, mtime=0)


def ar_member(name: str, contents: bytes) -> bytes:
    header = (
        f"{name:<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(contents):<10}`\n"
    ).encode("ascii")
    if len(header) != 60:
        raise ValueError("Invalid ar member header")
    return header + contents + (b"\n" if len(contents) % 2 else b"")


def build_library() -> Path:
    BUILD.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)
    source = ROOT / "xhs_no_refresh"
    test = BUILD / "test-policy"
    run("xcrun", "clang", "-fobjc-arc", "-Wall", "-Wextra", "-Werror",
        "-framework", "Foundation", str(source / "NoRefreshPolicy.m"),
        str(source / "test_policy.m"), "-o", str(test))
    print(run(str(test)))

    sdk = run("xcrun", "--sdk", "iphoneos", "--show-sdk-path").strip()
    slices: list[str] = []
    for arch in ("arm64", "arm64e"):
        output = BUILD / f"{LIBRARY}.{arch}"
        run("xcrun", "clang", "-target", f"{arch}-apple-ios14.0", "-isysroot", sdk,
            "-dynamiclib", "-fobjc-arc", "-Wall", "-Wextra", "-Werror",
            "-framework", "Foundation", "-framework", "UIKit",
            "-Wl,-install_name,@rpath/" + LIBRARY,
            "-Wl,-current_version," + VERSION,
            "-Wl,-compatibility_version," + VERSION,
            str(source / "NoRefreshPolicy.m"), str(source / "XHSNoRefresh.m"),
            "-o", str(output))
        slices.append(str(output))
    library = DIST / LIBRARY
    run("xcrun", "lipo", "-create", *slices, "-output", str(library))
    run("codesign", "--force", "--sign", "-", "--timestamp=none", str(library))
    run("codesign", "--verify", "--strict", str(library))
    if set(run("xcrun", "lipo", "-archs", str(library)).split()) != {"arm64", "arm64e"}:
        raise RuntimeError("Expected arm64 and arm64e slices")
    # TrollStore/TrollFools users inject this universal dylib directly.  The
    # `1-trollstore` suffix is intentional: it distinguishes this non-DEB
    # artifact from the three jailbreak packages in source listings.
    shutil.copyfile(library, DIST / TROLLSTORE_ARTIFACT)
    # Keep the original machine-friendly filename as a compatibility alias for
    # existing local users; the Chinese name is the canonical published file.
    shutil.copyfile(library, DIST / f"XHSNoRefresh_{VERSION}_TrollStore.dylib")
    return library


def build_deb(library: Path, variant: Variant) -> Path:
    prefix = f"{variant.data_prefix}/" if variant.data_prefix else ""
    base = prefix + "Library/MobileSubstrate/DynamicLibraries/"
    files = {
        base + LIBRARY: (library.read_bytes(), 0o755),
        base + "XHSNoRefresh.plist": (
            plistlib.dumps({"Filter": {"Bundles": [
                "com.xingin.xhs", "com.xingin.discover"
            ]}}), 0o644),
        f"{prefix}usr/share/doc/{PACKAGE}/README.md": (
            (ROOT / "xhs_no_refresh/README.md").read_bytes(), 0o644),
    }
    control = (
        f"Package: {PACKAGE}\nName: {DISPLAY_NAME} / XHS No Startup Refresh ({variant.label})\n"
        f"Version: {variant.package_version}\nArchitecture: {variant.architecture}\n"
        "Section: Tweaks\nPriority: optional\n"
        "Maintainer: Local Compatibility Build\n"
        "Depends: firmware (>= 15.0), mobilesubstrate\n"
        "Description: Keep Xiaohongshu homefeed stable on app activation\n"
        " Blocks only the initial homefeed refresh until the user interacts.\n"
        " Manual pulls and paginated requests remain available.\n"
    ).encode()
    sums = "".join(f"{hashlib.md5(value[0]).hexdigest()}  {name}\n"
                    for name, value in sorted(files.items())).encode()
    members = {
        "debian-binary": b"2.0\n",
        "control.tar.gz": tar_gz({"control": (control, 0o644),
                                   "md5sums": (sums, 0o644)}),
        "data.tar.gz": tar_gz(files),
    }
    target = DIST / f"{DISPLAY_NAME}-{VERSION}-{variant.suffix}.deb"
    target.write_bytes(b"!<arch>\n" + b"".join(
        ar_member(name, contents) for name, contents in members.items()))
    return target


def main() -> None:
    library = build_library()
    for variant in VARIANTS:
        print(f"{variant.label} deb:", build_deb(library, variant))
    print("TrollStore dylib:", DIST / TROLLSTORE_ARTIFACT)
    print("Device startup behavior: not tested on a phone.")


if __name__ == "__main__":
    main()
