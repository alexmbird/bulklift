import unittest
from pathlib import Path
import tempfile

from test.fakesourcetree import FakeSourceTreeAlbum
from util.file import is_audio_dir
from util.sanitize import dummy_sanitize, vfat_sanitize
from util.data import dict_not_nulls, available_cpu_count


class TestDictNotNulls(unittest.TestCase):

  def test_dict_not_nulls(self):
    "dict_not_nulls() recursively strips pairs with empty-values"
    d1 = dict_not_nulls({'a': 1, 'b': None, 'c': {}, 'd': {'z':None}, 'e': {'y':1}})
    assert 'a' in d1
    assert 'b' not in d1
    assert 'c' not in d1
    assert 'd' not in d1
    assert 'e' in d1


class TestCpuCount(unittest.TestCase):

  def test_available_cpu_count(self):
    "available_cpu_count() returns a number of cpus"
    cc = available_cpu_count()
    assert cc > 0
    assert cc == int(cc)


class TestVfatSanitize(unittest.TestCase):

  def test_vfat_sanitize(self):
    "Sanitize filenames for vfat"
    self.assertEqual(vfat_sanitize(Path('relative/p>th')), Path('relative/pth'))
    self.assertEqual(vfat_sanitize(Path('/this/is/fi ne')), Path('/this/is/fi ne'))
    self.assertEqual(vfat_sanitize(Path('/this/<s/?not')), Path('/this/s/not'))
    self.assertEqual(
      vfat_sanitize(Path('/this/<s/?not'), replace='_'),
      Path('/this/_s/_not')
    )


class TestIsAudioDir(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    """ Create a temp dir for tests """
    cls.TEMPDIR = tempfile.TemporaryDirectory('bulklift_tests')
    cls.TEMPPATH = Path(cls.TEMPDIR.name)
    cls.INPUT_PATH = cls.TEMPPATH / 'source'
    cls.INPUT_PATH.mkdir()
    cls.FAKE_ALBUM = FakeSourceTreeAlbum(base_path=cls.INPUT_PATH)
    cls.EMPTY_ALBUM_PATH = cls.INPUT_PATH / 'empty_dir'
    cls.EMPTY_ALBUM_PATH.mkdir()
    cls.OUTPUT_PATH = cls.TEMPPATH / 'output'
    cls.OUTPUT_PATH.mkdir()

  @classmethod
  def tearDownClass(cls):
    """ Remove temp dir """
    cls.TEMPDIR.cleanup()

  def test_is_audio_dir(self):
    "is_audio_dir() corectly identifies audio dirs"
    self.assertTrue(is_audio_dir(self.FAKE_ALBUM.path))
    self.assertFalse(is_audio_dir(self.EMPTY_ALBUM_PATH))

