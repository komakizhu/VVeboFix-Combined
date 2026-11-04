#!/usr/bin/env python3
"""Package-layout checks for the four published XHS artifacts."""

from __future__ import annotations

import subprocess
import unittest

from . import build


class PublishedVariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build.main()

    def package_fields(self, path):
        output = subprocess.check_output(["dpkg-deb", "-f", str(path)], text=True)
        fields = {}
        for line in output.splitlines():
            key, separator, value = line.partition(":")
            if separator:
                fields[key] = value.strip()
        return fields

    def package_paths(self, path):
        output = subprocess.check_output(["dpkg-deb", "-c", str(path)], text=True)
        return [line.rsplit(" ", 1)[-1] for line in output.splitlines()]

    def test_deb_variants_have_distinct_metadata_and_layouts(self):
        expected = {
            "rootful": ("iphoneos-arm", "Library/MobileSubstrate/DynamicLibraries/XHSNoRefresh.dylib"),
            "rootless": ("iphoneos-arm64", "var/jb/Library/MobileSubstrate/DynamicLibraries/XHSNoRefresh.dylib"),
            "roothide": ("iphoneos-arm64e", "Library/MobileSubstrate/DynamicLibraries/XHSNoRefresh.dylib"),
        }
        for variant in build.VARIANTS:
            path = build.DIST / f"{build.DISPLAY_NAME}-{build.VERSION}-{variant.suffix}.deb"
            self.assertTrue(path.is_file(), path)
            fields = self.package_fields(path)
            self.assertEqual(fields["Package"], build.PACKAGE)
            self.assertEqual(fields["Version"], variant.package_version)
            self.assertEqual(fields["Architecture"], expected[variant.suffix][0])
            paths = self.package_paths(path)
            self.assertIn("./" + expected[variant.suffix][1], paths)
            self.assertTrue(any(item.endswith("XHSNoRefresh.plist") for item in paths))

    def test_trollstore_artifact_is_universal_and_signed(self):
        artifact = build.DIST / build.TROLLSTORE_ARTIFACT
        self.assertTrue(artifact.is_file(), artifact)
        archs = subprocess.check_output(["xcrun", "lipo", "-archs", str(artifact)], text=True).split()
        self.assertEqual(set(archs), {"arm64", "arm64e"})
        subprocess.run(["codesign", "--verify", "--strict", str(artifact)], check=True)


if __name__ == "__main__":
    unittest.main()
