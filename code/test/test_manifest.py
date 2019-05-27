import unittest
from pathlib import Path

from manifest import Manifest, ManifestError


class TestManifest(unittest.TestCase):

  def test_LoadNoRoot(self):
    "Raise exception if root is missing"
    with self.assertRaises(ManifestError):
      man_noroot = Manifest.fromDir(Path('/'))

  @unittest.skip("not yet")
  def test_makeTemplate(self):
    "Manifest generates templates for new dirs"
