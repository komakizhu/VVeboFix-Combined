#!/usr/bin/env python3
"""Build one universal VVeboFix library, a RootHide deb and a TrollStore IPA."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import plistlib
import shutil
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from build_package import ar_member, tar_gz
from purchase_compat import build as app_tools

VERSION = "1.1.0"
PACKAGE = "com.lhl.vvebofix"
UPSTREAM_SOURCE = (
    "https://raw.githubusercontent.com/nildeveloper/VVeboFix/"
    "201d20697188de69d7e7557952ef02eee6158748/VVeboFix.m"
)
BUILD = ROOT / "build/combined"
DIST = ROOT / "dist/combined"
run = app_tools.run


def prepare_sources() -> list[str]:
    upstream = ROOT / "combined/upstream/VVeboFix.m"
    if upstream.is_file():
        network = upstream.read_text()
    else:
        request = Request(UPSTREAM_SOURCE, headers={"User-Agent": "VVeboFix-Combined-build"})
        with urlopen(request, timeout=30) as response:
            network = response.read().decode("utf-8")
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "upstream-VVeboFix.m").write_text(network)
    network = network.replace("#import <UIKit/UIKit.h>", "")
    network = network.replace("static BOOL const kDebugEnabled = YES;", "static BOOL const kDebugEnabled = NO;")
    for name in ("ProcessProfileStatusesResponse", "ProcessCardlistResponse"):
        signature = f"static NSData * {name}(NSData *originalData, NSString *urlString) {{"
        assert network.count(signature) == 1
        network = network.replace(signature, signature + "\n    (void)urlString;")
    initializer = "__attribute__((constructor))\nstatic void VVeboFixInit(void)"
    assert network.count(initializer) == 1
    network = network.replace(initializer, "void VVInstallNetworkCompatibility(void)")
    network += '''
#if VV_COMPAT_TESTING
NSURLRequest *VVTestRewrite(NSURLRequest *r) { return RewriteRequestIfNeeded(r); }
NSData *VVTestResponse(NSData *d, NSString *u) { return ProcessResponseData(d, u); }
Class VVTestProtocolClass(void) { return VVeboFixURLProtocol.class; }
#endif
'''
    purchase = (ROOT / "purchase_compat/VVeboPurchaseCompat.m").read_text()
    purchase = purchase.split("#if VV_COMPAT_TESTING", 1)[0]
    purchase = purchase.replace("static BOOL VVInstallCompatibility(Class storeClass)",
                                "BOOL VVInstallPurchaseCompatibility(Class storeClass)")
    purchase += '''
#if VV_COMPAT_TESTING
BOOL VVInstallCompatibilityForTests(Class c) { return VVInstallPurchaseCompatibility(c); }
#endif
'''
    (BUILD / "NetworkFix.m").write_text(network)
    (BUILD / "PurchaseFix.m").write_text(purchase)
    return [str(BUILD / "NetworkFix.m"), str(BUILD / "PurchaseFix.m"),
            str(ROOT / "combined/Loader.m")]


def build_library() -> Path:
    BUILD.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)
    sources = prepare_sources()
    options = ("-fobjc-arc", "-Wall", "-Wextra", "-Werror", "-framework", "Foundation")
    purchase_test = BUILD / "test-purchase"
    run("xcrun", "clang", *options, "-DVV_COMPAT_TESTING=1", *sources,
        str(ROOT / "purchase_compat/test_compat.m"), "-o", str(purchase_test))
    print(run(str(purchase_test), "--startup"))
    print(run(str(purchase_test)))
    network_test = BUILD / "test-combined"
    run("xcrun", "clang", *options, "-DVV_COMPAT_TESTING=1", *sources,
        str(ROOT / "combined/test_combined.m"), "-o", str(network_test))
    print(run(str(network_test)))
    sdk = run("xcrun", "--sdk", "iphoneos", "--show-sdk-path").strip()
    slices = []
    for arch in ("arm64", "arm64e"):
        output = BUILD / f"VVeboFix.{arch}.dylib"
        run("xcrun", "clang", "-target", f"{arch}-apple-ios14.0", "-isysroot", sdk,
            "-dynamiclib", *options, "-fvisibility=hidden", "-DVV_COMPAT_TESTING=0",
            "-Wl,-install_name,@rpath/VVeboFix.dylib", "-Wl,-current_version," + VERSION,
            "-Wl,-compatibility_version,1.0.0", *sources, "-o", str(output))
        slices.append(str(output))
    library = DIST / "VVeboFix.dylib"
    run("xcrun", "lipo", "-create", *slices, "-output", str(library))
    run("codesign", "--force", "--sign", "-", "--timestamp=none", str(library))
    run("codesign", "--verify", "--strict", str(library))
    assert set(run("xcrun", "lipo", "-archs", str(library)).split()) == {"arm64", "arm64e"}
    shutil.copyfile(library, DIST / f"VVeboFix_Combined_{VERSION}_TrollStore.dylib")
    return library


def build_deb(library: Path) -> Path:
    base = "Library/MobileSubstrate/DynamicLibraries/"
    files = {
        base + "VVeboFix.dylib": (library.read_bytes(), 0o755),
        base + "VVeboFix.plist": (plistlib.dumps({"Filter": {"Bundles": ["com.johnil.vvebo"]}}), 0o644),
        f"usr/share/doc/{PACKAGE}/README.zh-CN.md": ((ROOT / "combined/README.md").read_bytes(), 0o644),
        f"usr/share/doc/{PACKAGE}/UPSTREAM.md": ((ROOT / "combined/UPSTREAM.md").read_bytes(), 0o644),
    }
    control = (
        f"Package: {PACKAGE}\nName: VVeboFix 合并版 (RootHide)\nVersion: {VERSION}\n"
        "Architecture: iphoneos-arm64e\nSection: Tweaks\nPriority: optional\n"
        "Maintainer: Local Compatibility Build\n"
        "Depends: firmware (>= 15.0), mobilesubstrate\n"
        "Conflicts: com.local.vvebo.purchasecompat, com.yourcompany.vvebofix\n"
        "Replaces: com.local.vvebo.purchasecompat, com.yourcompany.vvebofix\n"
        "Description: Combined VVebo API fix and local purchase compatibility\n"
        " Single universal library for VVebo 3.3.31. Device testing required.\n"
    ).encode()
    sums = "".join(f"{hashlib.md5(value[0]).hexdigest()}  {name}\n"
                   for name, value in sorted(files.items())).encode()
    timestamp = int((ROOT / "combined/Loader.m").stat().st_mtime)
    members = {"debian-binary": b"2.0\n",
               "control.tar.gz": tar_gz({"control": (control, 0o644), "md5sums": (sums, 0o644)}, timestamp),
               "data.tar.gz": tar_gz(files, timestamp)}
    target = DIST / f"{PACKAGE}_{VERSION}_iphoneos-arm64e.deb"
    target.write_bytes(b"!<arch>\n" + b"".join(ar_member(k, v, timestamp) for k, v in members.items()))
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ipa", type=Path, help="Original full-permissions VVebo 3.3.31 IPA")
    args = parser.parse_args()
    library = build_library()
    print("RootHide deb:", build_deb(library))
    if args.ipa:
        app_tools.BUILD = BUILD
        app_tools.DIST = DIST
        app_tools.VERSION = VERSION
        app_tools.LIBRARY = "VVeboFix.dylib"
        result = app_tools.build_ipa(args.ipa, library)
        renamed = DIST / f"VVebo_3.3.31_Combined_{VERSION}_TrollStore.ipa"
        result.replace(renamed)
        print("TrollStore IPA:", renamed)
    print("Universal TrollStore library:", DIST / f"VVeboFix_Combined_{VERSION}_TrollStore.dylib")
    print("Phone startup, API access, purchased features and real iCloud sync: not tested.")


if __name__ == "__main__":
    main()
