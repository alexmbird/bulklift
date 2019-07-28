import unittest
import tempfile
from pathlib import Path
import shutil

from test.fakesourcetree import FakeSourceTreeAlbum
from output import OutputTree, OutputAlbum
from manifest import ManifestConfig, ManifestOutput
from wrappers import FFmpegWrapper
from signature import Signature


class TestOutputTree(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    """ Create a temp dir for tests """
    cls.TEMPDIR = tempfile.TemporaryDirectory('bulklift_tests')
    cls.TEMPPATH = Path(cls.TEMPDIR.name)

  @classmethod
  def tearDownClass(cls):
    """ Remove temp dir """
    cls.TEMPDIR.cleanup()

  def test_clean(self):
    "OutputTree removes redundant dirs"
    otree = OutputTree(self.TEMPPATH)
    good_dir = self.TEMPPATH / 'used_dir_5694'
    good_dir.mkdir()
    bad_dir = self.TEMPPATH / 'unused_dir_53416'
    bad_dir.mkdir()
    otree.cleanup(expected_dirs=[good_dir], verbose=False)
    self.assertTrue(good_dir.exists())
    self.assertFalse(bad_dir.exists())
    self.assertTrue(self.TEMPPATH.is_dir()) # don't delete the root

  @unittest.skip("not written yet")
  def test_permissions(self):
    "OutputTree recursively changes ownership & permissions"
    assert False


class TestOutputAlbum(unittest.TestCase):
  """ Test output album representation """

  METADATA = {
    'artist': "DJ Bulklift",
    'album': "Greatest Hits",
    'year': 2019,
    'genre': "Silencecore"
  }

  @classmethod
  def setUpClass(cls):
    """ Create a temp dir for tests """
    cls.TEMPDIR = tempfile.TemporaryDirectory('bulklift_tests')
    cls.TEMPPATH = Path(cls.TEMPDIR.name)
    cls.INPUT_PATH = cls.TEMPPATH / 'source'
    cls.INPUT_PATH.mkdir()
    cls.FAKE_ALBUM = FakeSourceTreeAlbum(base_path=cls.INPUT_PATH)
    cls.OUTPUT_PATH = cls.TEMPPATH / 'output'

  @classmethod
  def tearDownClass(cls):
    """ Remove temp dir """
    cls.TEMPDIR.cleanup()

  def setUp(self):
    self.OUTPUT_PATH.mkdir()  # fresh output dir for every test

  def tearDown(self):
    shutil.rmtree(self.OUTPUT_PATH)  # fresh output dir for every test

  def _makeOutputAlbum(self, album_name, formats=['opus']):
    """ Create an OutputAlbum + metadata + configs suitable for tests """
    mconfig = ManifestConfig()
    oconfig = ManifestOutput({'path':self.OUTPUT_PATH, 'formats':formats})
    metadata = self.METADATA.copy()
    metadata['album'] = album_name
    oa = OutputAlbum(mconfig, oconfig, metadata)
    oa.path.mkdir(parents=True, exist_ok=True)
    return (mconfig, oconfig, metadata, oa)

  def test_album_path(self):
    "OutputAlbum generates name/path for output dir"
    mconfig = ManifestConfig()
    metadata = self.METADATA.copy()
    metadata['album'] = "Greatest Hits (test_album_dir)"
    oa_opus = OutputAlbum(
      mconfig,
      ManifestOutput({'path':self.OUTPUT_PATH, 'formats':['opus']}),
      metadata
    )
    self.assertEqual(
      oa_opus.albumPath(metadata),
      self.OUTPUT_PATH / 'Silencecore/DJ Bulklift/2019 Greatest Hits (test_album_dir)'
    )

  def test_incorporate_lossless(self):
    "OutputAlbum incorporates lossless source into desired format"
    mconfig = ManifestConfig()
    metadata = self.METADATA.copy()
    metadata['album'] = "Greatest Hits (test_filter)"
    oa_opus = OutputAlbum(
      mconfig,
      ManifestOutput({'path':self.OUTPUT_PATH, 'formats':['opus']}),
      metadata
    )
    oa_mp3 = OutputAlbum(
      mconfig,
      ManifestOutput({'path':self.OUTPUT_PATH, 'formats':['mp3']}),
      metadata
    )
    oa_copy = OutputAlbum(
      mconfig,
      ManifestOutput({'path':self.OUTPUT_PATH, 'formats':['copy']}),
      metadata
    )
    source_t = self.FAKE_ALBUM.tracks[1]
    ffmpeg = FFmpegWrapper(source_path=source_t)
    oa_opus.incorporate(source_t, ffmpeg)
    oa_mp3.incorporate(source_t, ffmpeg)
    oa_copy.incorporate(source_t, ffmpeg)
    self.assertEqual(ffmpeg.expected_outputs[0].name, source_t.with_suffix('.opus').name)
    self.assertEqual(ffmpeg.expected_outputs[1].name, source_t.with_suffix('.mp3').name)
    self.assertEqual(ffmpeg.expected_outputs[2].name, source_t.with_suffix('.flac').name)

  def test_filter(self):
    "OutputAlbum correctly filters input tracks"
    mconfig, oconfig, metadata, oa = self._makeOutputAlbum("album 1")
    oconfig['filters'] = {'include': ['05*'], 'exclude': []}
    self.assertTrue(oa.isFilterAllowed(self.FAKE_ALBUM.tracks[5]))
    self.assertFalse(oa.isFilterAllowed(self.FAKE_ALBUM.tracks[7]))
    oconfig['filters'] = {'include': ['05*'], 'exclude': ['07*']}
    self.assertTrue(oa.isFilterAllowed(self.FAKE_ALBUM.tracks[5]))
    self.assertFalse(oa.isFilterAllowed(self.FAKE_ALBUM.tracks[7]))
    self.assertFalse(oa.isFilterAllowed(self.FAKE_ALBUM.tracks[3]))
    oconfig['filters'] = {'include': [], 'exclude': ['07*']}
    self.assertFalse(oa.isFilterAllowed(self.FAKE_ALBUM.tracks[7]))
    self.assertTrue(oa.isFilterAllowed(self.FAKE_ALBUM.tracks[3]))

  def test_finalize(self):
    "OutputAlbum finalize()"
    mconfig, oconfig, metadata, oa = self._makeOutputAlbum("album 2")
    ffmpeg_art = FFmpegWrapper(source_path=self.FAKE_ALBUM.cover_gif)
    oa.incorporate(self.FAKE_ALBUM.cover_gif, ffmpeg_art) # no audio yet
    self.assertEqual(len(ffmpeg_art), 0)
    source_t = self.FAKE_ALBUM.tracks[1]
    ffmpeg_track = FFmpegWrapper(source_path=source_t)
    oa.incorporate(source_t, ffmpeg_track) # add audio
    self.assertEqual(len(ffmpeg_track), 1)
    ffmpeg_track.run()    # creates output dir
    stray_file = oa.path / 'stray_file.txt'           # should be deleted
    stray_file.touch()
    oa.finalize(verbose=False)
    output_album_cover = oa.path / self.FAKE_ALBUM.cover_gif.name
    self.assertTrue(output_album_cover.is_file())     # artwork now copied
    self.assertFalse(stray_file.exists())             # orphan is deleted

  def test_signature_created(self):
    "OutputAlbum adds signature"
    mconfig, oconfig, metadata, oa = self._makeOutputAlbum("album 3")
    source9 = self.FAKE_ALBUM.tracks[9]
    ffmpeg = FFmpegWrapper(source_path=source9)
    oa.incorporate(source9, ffmpeg)
    ffmpeg.run()
    sig_file = oa.path / Signature.SIGNATURE_FILE_NAME
    self.assertFalse(sig_file.is_file())
    oa.finalize(verbose=False)
    self.assertEqual(len(oa.signature), 1)
    self.assertTrue(sig_file.is_file())

  def test_regenerate_no(self):
    "OutputAlbum leaves existing target unmolested if source doesn't change"
    mconfig, oconfig, metadata, oa = self._makeOutputAlbum("album 4")
    self.assertFalse(oa.dirty)
    for source_t in self.FAKE_ALBUM.tracks.values():
      ffmpeg = FFmpegWrapper(source_path=source_t)
      oa.incorporate(source_t, ffmpeg)
      ffmpeg.run()
    self.assertTrue(oa.dirty)
    oa.finalize(verbose=False)
    mconfig, oconfig, metadata, oa = self._makeOutputAlbum("album 4")
    self.assertEqual(len(oa.signature), len(self.FAKE_ALBUM.tracks))
    for source_t in self.FAKE_ALBUM.tracks.values():
      ffmpeg = FFmpegWrapper(source_path=source_t)
      oa.incorporate(source_t, ffmpeg)
      self.assertEqual(len(ffmpeg), 0)
    self.assertFalse(oa.dirty)

  def test_regenerate_changed_source(self):
    "OutputAlbum replaces media in target if source has changed"
    fake_album = FakeSourceTreeAlbum(base_path=self.INPUT_PATH, name="test_regenerate_changed_source")

    # Transcode
    mconfig, oconfig, metadata, oa = self._makeOutputAlbum("album 5")
    self.assertFalse(oa.dirty)
    for source_t in fake_album.tracks.values():
      ffmpeg = FFmpegWrapper(source_path=source_t)
      oa.incorporate(source_t, ffmpeg)
      ffmpeg.run()
    self.assertTrue(oa.dirty)
    oa.finalize(verbose=False)

    # Alter the source
    for n, source_t in list(fake_album.tracks.items()):
      new_name = source_t.parent / '{:02d} - different name.flac'.format(n)
      source_t.rename(new_name)
      fake_album.tracks[n] = new_name

    # Transcode again
    mconfig, oconfig, metadata, oa = self._makeOutputAlbum("album 5")
    self.assertEqual(len(oa.signature), len(fake_album.tracks))
    for n, source_t in fake_album.tracks.items():
      ffmpeg = FFmpegWrapper(source_path=new_name)
      oa.incorporate(source_t, ffmpeg)
      self.assertEqual(len(ffmpeg), 1)
      ffmpeg.run()
    self.assertTrue(oa.dirty)
    files_in_dir = list(oa.path.iterdir())
    self.assertEqual(len(files_in_dir) - 1, len(fake_album.tracks) * 2)
    oa.finalize(verbose=False)  # deletes dupes
    self.assertEqual(len(oa.signature), len(fake_album.tracks))

    # Dupes are gone
    files_in_dir = list(oa.path.iterdir())
    self.assertEqual(len(files_in_dir) - 1, len(fake_album.tracks))

  def test_regenerate_changed_target(self):
    "OutputAlbum replaces media in target if it is missing"
    fake_album = FakeSourceTreeAlbum(base_path=self.INPUT_PATH, name="test_regenerate_changed_target")

    # Transcode
    mconfig, oconfig, metadata, oa = self._makeOutputAlbum("album 6")
    self.assertFalse(oa.dirty)
    for source_t in fake_album.tracks.values():
      ffmpeg = FFmpegWrapper(source_path=source_t)
      oa.incorporate(source_t, ffmpeg)
      ffmpeg.run()
    oa.finalize(verbose=False)
    self.assertEqual(len(oa.signature), len(fake_album.tracks))

    # Remove track 7 from output
    next(oa.path.glob('07*')).unlink()
    files_in_dir = list(oa.path.iterdir())
    self.assertEqual(len(files_in_dir) + 1, len(fake_album.tracks) + 1)

    # Transcode again
    mconfig, oconfig, metadata, oa = self._makeOutputAlbum("album 6")
    for n, source_t in fake_album.tracks.items():
      ffmpeg = FFmpegWrapper(source_path=source_t)
      oa.incorporate(source_t, ffmpeg)
      if source_t.name.startswith('07'):
        self.assertEqual(len(ffmpeg), 1)
        ffmpeg.run()
      else:
        self.assertEqual(len(ffmpeg), 0)
    self.assertTrue(oa.dirty)
    oa.finalize(verbose=False)  # deletes dupes
    self.assertFalse(oa.dirty)

    # it is replaced
    files_in_dir = list(oa.path.iterdir())
    self.assertEqual(len(files_in_dir), len(fake_album.tracks) + 1)
