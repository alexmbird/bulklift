import unittest
from pathlib import Path
import tempfile

from manifest import Manifest, ManifestError


class TestManifest(unittest.TestCase):

  def test_LoadNoRoot(self):
    "Raise exception if root is missing"
    with self.assertRaises(ManifestError):
      man_noroot = Manifest.fromDir(Path('/'))

  @unittest.skip("not yet")
  def test_makeTemplate(self):
    "Manifest generates templates for new dirs"

  def test_exists(self):
    "Manifest detects whether a .bulklift.yaml is present"
    with tempfile.TemporaryDirectory() as tmpdir:
      has_yaml_dir = Path(tmpdir) / 'HasYaml'
      has_yaml_dir.mkdir()
      has_yaml_dir.joinpath(Manifest.MANIFEST_FILE_NAME).touch()
      m = Manifest(has_yaml_dir)
      self.assertTrue(m.exists())
      no_yaml_dir = Path(tmpdir) / 'NoYaml'
      no_yaml_dir.mkdir()
      m = Manifest(no_yaml_dir)
      self.assertFalse(m.exists())
