"""Check artwork provenance, renderer compatibility, and fallback coverage."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from test_build_zen_packs import builder


class GlyphsIconsTest(unittest.TestCase):
    def test_sources_match_inventory_and_use_supported_svg_elements(self):
        root = builder.ROOT
        inventory = json.loads((root / "icon-sources.json").read_text())
        files = {str(path.relative_to(root)): path
                 for path in (root / "Glyphs Poly").rglob("*.svg")}
        self.assertEqual(set(files), set(inventory["icons"]))
        self.assertEqual(inventory["license"]["spdx"], "MIT")
        self.assertFalse(list(root.glob("Solar *")))
        supported = {"svg", "g", "path", "rect", "circle", "ellipse", "line",
                     "polyline", "polygon"}
        for name, path in files.items():
            with self.subTest(icon=name):
                source = inventory["icons"][name]
                self.assertTrue(source["icon"].startswith("glyphs-poly:"))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])
                svg = ET.fromstring(path.read_bytes())
                self.assertTrue(all(node.tag.rsplit("}", 1)[-1] in supported for node in svg.iter()))
                self.assertFalse(any(key.rsplit("}", 1)[-1] == "href"
                                     for node in svg.iter() for key in node.attrib))

    def test_unsupported_controls_keep_fallback_and_states_are_distinct(self):
        root = builder.ROOT
        inventory = json.loads((root / "icon-sources.json").read_text())
        metadata = json.loads((root / "pack.json").read_text())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            pack, directories = next(builder.pack_sources(root, output))
            destination = builder.build_pack(pack, directories, root, output, None, metadata)
            with zipfile.ZipFile(destination) as archive:
                prefix = "zen-glyphs-poly/"
                names = {Path(name).stem for name in archive.namelist() if name.endswith(".svg")}
                self.assertFalse(set(inventory["omitted_source_lookups"]) & names)
                self.assertIs(json.loads(archive.read(prefix + "pack.json"))["color"], True)
                for names in (("star.empty", "star.full", "star.white"),
                              ("wifi.open.0", "wifi.open.25", "wifi.open.50",
                               "wifi.open.75", "wifi.open.100"),
                              ("tab_left", "tab_right"), ("sort_asc", "sort_desc")):
                    self.assertEqual(len({archive.read(prefix + name + ".svg") for name in names}),
                                     len(names))


if __name__ == "__main__":
    unittest.main()
