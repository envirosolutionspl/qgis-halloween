"""Tests of the build scripts and the plugin metadata."""

import configparser
import importlib.util
import tempfile
import unittest
import zipfile

from qgis_stub import ROOT


def load(name):
    """Import ``scripts/<name>.py`` as a module."""
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GeneratedFilesTest(unittest.TestCase):
    """The committed pictures are what the scripts produce."""

    def test_icons_are_up_to_date(self):
        """``icons/tool_*.svg`` and ``web.svg`` match ``build_icons.py``."""
        build_icons = load("build_icons")
        for name, text in build_icons.pictures().items():
            path = build_icons.ICON_DIR / name
            self.assertEqual(path.read_text(encoding="utf-8"), text, name)

    def test_stars_are_up_to_date(self):
        """Every theme's ``stars.svg`` matches ``build_stars.py``."""
        build_stars = load("build_stars")
        text = build_stars.stars()
        for folder in build_stars.THEMES_DIR.iterdir():
            path = folder / "stars.svg"
            self.assertEqual(path.read_text(encoding="utf-8"), text, folder)


class MetadataTest(unittest.TestCase):
    """``metadata.txt`` has what the QGIS plugin repository requires."""

    def setUp(self):
        """Read the metadata."""
        self.metadata = configparser.ConfigParser(interpolation=None)
        self.metadata.read(ROOT / "halloween_skin" / "metadata.txt",
                           encoding="utf-8")
        self.general = self.metadata["general"]

    def test_required_keys(self):
        """The mandatory keys are present."""
        for key in ("name", "qgisMinimumVersion", "description", "about",
                    "version", "author", "email", "repository"):
            self.assertTrue(self.general.get(key), key)

    def test_qt6_and_versions(self):
        """The plugin declares QGIS 3.40 - 4.x and Qt 6 support."""
        self.assertEqual(self.general["qgisMinimumVersion"], "3.40")
        self.assertEqual(self.general["supportsQt6"], "True")

    def test_changelog_starts_with_version(self):
        """The newest changelog entry is the current version."""
        first = self.general["changelog"].strip().splitlines()[0]
        self.assertTrue(first.startswith(self.general["version"] + " "))

    def test_icon_exists(self):
        """The plugin icon named in the metadata exists."""
        self.assertTrue(
            (ROOT / "halloween_skin" / self.general["icon"]).is_file())


class PackageTest(unittest.TestCase):
    """The ZIP built by ``package.py``."""

    def test_zip_contents(self):
        """The ZIP holds the plugin folder and nothing else."""
        package = load("package")
        with tempfile.TemporaryDirectory() as tmp:
            target = package.build(tmp)
            self.assertEqual(target.name, "halloween_skin-{}.zip".format(
                package.version()))
            with zipfile.ZipFile(target) as archive:
                names = archive.namelist()
        self.assertIn("halloween_skin/metadata.txt", names)
        self.assertIn("halloween_skin/fonts/Nosifer-Regular.ttf", names)
        self.assertTrue(all(n.startswith("halloween_skin/") for n in names))
        self.assertFalse(any("__pycache__" in n or n.endswith(".pyc")
                             for n in names))


if __name__ == "__main__":
    unittest.main()
