import unittest
import tempfile
from copy import deepcopy
from pathlib import Path

from test.fakesourcetree import FakeSourceTreeAlbum

from manifest import ManifestConfig, ManifestOutput, MetadataError
from input import InputAlbum


class TestInputAlbum(unittest.TestCase):
  """ Test the input album representation """

  METADATA = {
    'artist': "DJ Bulklift",
    'album': "Greatest Hits",
    'year': 2019,
    'genre': "Silencecore"
  }

  BASIC_CONFIG = {
    'transcoding': {
      'ffmpeg_path': '/usr/local/bin/ffmpeg',  # default ubuntu 18 doesn't work
      'rewrite_metadata': {
        'artist': '{artist}',
        'track': '',
        'album': None
      }
    }
  }

  @classmethod
  def setUpClass(cls):
    """ Create a temp dir for tests """
    cls.TEMPDIR = tempfile.TemporaryDirectory('bulklift_tests')
    cls.TEMPPATH = Path(cls.TEMPDIR.name)
    cls.INPUT_PATH = cls.TEMPPATH / 'source'
    cls.INPUT_PATH.mkdir()
    cls.FAKE_ALBUM = FakeSourceTreeAlbum(base_path=cls.INPUT_PATH)
    cls.OUTPUTA_PATH = cls.TEMPPATH / 'outputA'
    cls.OUTPUTA_PATH.mkdir()
    cls.OUTPUTB_PATH = cls.TEMPPATH / 'outputB'
    cls.OUTPUTB_PATH.mkdir()

  @classmethod
  def tearDownClass(cls):
    """ Remove temp dir """
    cls.TEMPDIR.cleanup()

  def test_files(self):
    "InputAlbum correctly lists files"
    ia = InputAlbum(
      self.FAKE_ALBUM.path, ManifestConfig(self.BASIC_CONFIG), [],
      metadata=self.METADATA
    )
    files = ia.files()
    self.assertEqual(len(files), 11)  # 10 tracks + cover.gif
    self.assertEqual(                 # smallest file last
      files[-1].name,
      self.FAKE_ALBUM.cover_gif.name
    )

  def test_bakeMetadata(self):
    "InputAlbum.bakeMetadata() correctly rewrites metadata"
    ia = InputAlbum(
      self.FAKE_ALBUM.path, ManifestConfig(self.BASIC_CONFIG), [],
      metadata=self.METADATA
    )
    self.assertEqual(
      ia.metadata_rewrites,
      {'track': '', 'artist': 'DJ Bulklift', 'comment': ''}
    )

  def test_missingMetadata(self):
    "InputAlbum.bakeMetadata() catches metadata that is referenced but missing"
    broken_config = deepcopy(self.BASIC_CONFIG)
    broken_config['transcoding']['rewrite_metadata']['artist'] = '{not_here}'
    with self.assertRaises(MetadataError):
      ia = InputAlbum(
        self.FAKE_ALBUM.path, ManifestConfig(self.BASIC_CONFIG), [],
        metadata=broken_config
      )

  def test_transcode(self):
    "InputAlbum transcodes to multiple outputs"
    out_a = {'path': self.OUTPUTA_PATH, 'formats':['mp3'], 'enabled':True}
    out_b = {'path': self.OUTPUTB_PATH, 'formats':['opus'], 'enabled':True}
    ia = InputAlbum(
      self.FAKE_ALBUM.path,
      ManifestConfig(self.BASIC_CONFIG),
      [
        ManifestOutput(out_a),
        ManifestOutput(out_b)
      ],
      metadata=self.METADATA
    )
    import subprocess
    try:
      ia.transcode(verbose=False)
    except subprocess.CalledProcessError as spe:
      print("stdout: {}\nstderr: {}".format(spe.stdout, spe.stderr))

    output_mp3, output_opus = ia.output_albums
    for t in self.FAKE_ALBUM.tracks.values():
      self.assertTrue((output_mp3.path / t.name).with_suffix('.mp3').is_file())
      self.assertTrue((output_opus.path / t.name).with_suffix('.opus').is_file())
