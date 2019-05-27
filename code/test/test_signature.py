import unittest
import tempfile
from pathlib import Path
import copy

from test.fakesourcetree import FakeSourceTreeAlbum
from signature import Signature
from manifest import ManifestConfig, ManifestOutput


class TestSignature(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    """ Create a temp dir for tests """
    cls.TEMPDIR = tempfile.TemporaryDirectory('bulklift_tests')
    cls.TEMPPATH = Path(cls.TEMPDIR.name)
    cls.INPUT_PATH = cls.TEMPPATH / 'source'
    cls.INPUT_PATH.mkdir()
    cls.FAKE_ALBUM = FakeSourceTreeAlbum(base_path=cls.INPUT_PATH)
    cls.OUTPUT_PATH = cls.TEMPPATH / 'output'
    cls.OUTPUT_PATH.mkdir()
    cls.MCONF = ManifestConfig()  # basic manifest configs to use in sigs
    cls.OCONF = ManifestOutput({'path':cls.OUTPUT_PATH, 'formats':['opus']})

  @classmethod
  def tearDownClass(cls):
    """ Remove temp dir """
    cls.TEMPDIR.cleanup()

  def test_save_load(self):
    "Signature saves & loads a sig from output dir"
    s = Signature(self.OUTPUT_PATH, self.MCONF, self.OCONF)
    self.assertEqual(
      s.signature_file,
      self.OUTPUT_PATH / Signature.SIGNATURE_FILE_NAME
    )
    with self.assertRaises(FileNotFoundError):
      s.load()
    s.save(verbose=False)
    self.assertTrue(s.signature_file.is_file())
    s.load()

  def test_add(self):
    "Signature add()s new files"
    # NB: for convenience we are using the fake input album for both
    #     input and output.
    tracks = self.FAKE_ALBUM.tracks
    s = Signature(self.OUTPUT_PATH, self.MCONF, self.OCONF)
    self.assertEqual(len(s), 0)
    self.assertFalse(s.has(tracks[3].name, tracks[3], 'flac'))
    s.add(tracks[3].name, tracks[3], 'flac')
    self.assertEqual(len(s), 1)
    self.assertTrue(s.has(tracks[3].name, tracks[3], 'flac'))
    s.add(tracks[3].name, tracks[3], 'flac')
    self.assertEqual(len(s), 1)
    self.assertTrue(s.has(tracks[3].name, tracks[3], 'flac'))
    s.add(    # also test an image
      self.FAKE_ALBUM.cover_gif.name, self.FAKE_ALBUM.cover_gif, None
    )
    self.assertEqual(len(s), 2)
    self.assertTrue(
      s.has(self.FAKE_ALBUM.cover_gif.name, self.FAKE_ALBUM.cover_gif, None)
    )

  def test_clean(self):
    "Signature clean()s vanished files"
    # NB: for convenience we are using the fake input album for both
    #     input and output.
    tracks = self.FAKE_ALBUM.tracks
    s = Signature(self.OUTPUT_PATH, self.MCONF, self.OCONF)
    s.clean(verbose=False)  # nothing to do
    s.add(tracks[3].name, tracks[3], 'flac')
    self.assertEqual(len(s), 1)
    s.clean(verbose=False)
    self.assertEqual(len(s), 0)
    output_track = self.OUTPUT_PATH / tracks[3].name
    output_track.touch()
    s.add(tracks[3].name, tracks[3], 'flac')  # present and file exists
    self.assertEqual(len(s), 1)
    s.clean(verbose=False)
    self.assertEqual(len(s), 1)

  def test_signature_changes(self):
    "Signature changes with manifest config values"
    t = tracks = self.FAKE_ALBUM.tracks[7]
    s = Signature(self.OUTPUT_PATH, self.MCONF, self.OCONF)
    sig_orig = s.signature(t, codec=None)
    self.assertNotEqual(sig_orig, s.signature(t, codec='mp3'))
    self.assertNotEqual(sig_orig, s.signature(t, codec='opus'))
    s = Signature(
      self.OUTPUT_PATH, self.MCONF, self.OCONF, {'mdata':'rewrite'}
    )
    self.assertNotEqual(sig_orig, s.signature(t, codec=None))
    mconf = copy.deepcopy(self.MCONF)       # Change r128gain setting
    mconf['r128gain']['type'] = 'track'
    s = Signature(self.OUTPUT_PATH, mconf, self.OCONF)
    self.assertNotEqual(sig_orig, s.signature(t, codec=None))
