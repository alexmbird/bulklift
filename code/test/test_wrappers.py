import unittest
import tempfile
from pathlib import Path
from subprocess import CalledProcessError

from wrappers import ExternalCommandWrapper, R128gainWrapper, FFmpegWrapper, \
                     SoxWrapper, ExternalCommandError, NothingToDoError


class TestExternalCommandWrapper(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    """ Create a temp dir for tests """
    cls.TEMPDIR = tempfile.TemporaryDirectory('bulklift_tests')

  @classmethod
  def tearDownClass(cls):
    """ Remove temp dir """
    cls.TEMPDIR.cleanup()

  def test_invocation(self):
    "Invoke an ExternalCommandWrapper"
    ecr = ExternalCommandWrapper(binary='/bin/true')
    result = ecr.run()
    self.assertEqual(result.args[0], '/bin/true')
    self.assertEqual(result.returncode, 0)
    ecr = ExternalCommandWrapper(binary='/bin/false')
    with self.assertRaises(CalledProcessError):
      ecr.run()
    ecr = ExternalCommandWrapper(binary='/nonexistent/path/to/binary_345570')
    with self.assertRaises(FileNotFoundError):
      ecr.run()

  def test_expected_outputs(self):
    "ExternalCommandWrapper checks for expected outputs"
    file_present = Path(self.TEMPDIR.name) / 'empty_file'
    ecr = ExternalCommandWrapper(
      binary='/bin/touch', args=[file_present], expected_outputs=[file_present]
    )
    ecr.run()
    self.assertTrue(file_present.is_file())
    file_absent = Path(self.TEMPDIR.name) / 'missing_file'
    ecr = ExternalCommandWrapper(
      binary='/bin/true', expected_outputs=[file_absent]
    )
    with self.assertRaises(ExternalCommandError):
      ecr.run()
    self.assertFalse(file_absent.is_file())


class TestFFmpegWrapper(unittest.TestCase):

  METADATA = {'artist':'DJ Bulklift'}

  @classmethod
  def setUpClass(cls):
    """ Create a temp dir for test audio and an empty .flac file within """
    cls.TEMPDIR = tempfile.TemporaryDirectory('_bulklift_tests')
    cls.INPUT_FLAC = Path(cls.TEMPDIR.name) / 'test.flac'
    silence = SoxWrapper(output_path=cls.INPUT_FLAC)
    silence.run()

  @classmethod
  def tearDownClass(cls):
    """ Remove temp dir """
    # import time; time.sleep(666)
    cls.TEMPDIR.cleanup()

  def test_invocation(self):
    "Invoke a TestFFmpegWrapper"
    ffmpeg = FFmpegWrapper(source_path=self.INPUT_FLAC)
    with self.assertRaises(NothingToDoError):
      result = ffmpeg.run()  # no args, will error

  def test_metadataOpts(self):
    "FFmpegWrapper generates metadata options"
    opts = FFmpegWrapper.metadataOpts({'foo':'bar'})
    self.assertIsInstance(opts, list)
    self.assertEqual(opts, ['-metadata', 'foo=bar', '-metadata:s:a', 'foo=bar'])

  def test_transcode_flac_mp3(self):
    "FFmpegWrapper transcodes flac to mp3"
    ffmpeg = FFmpegWrapper(self.INPUT_FLAC, metadata=self.METADATA)
    output_file = Path(self.TEMPDIR.name) / 'test_a.mp3'
    ffmpeg.appendOutputLame(output_file)
    ffmpeg.run()
    self.assertTrue(output_file.is_file())

  def test_transcode_flac_opus(self):
    "FFmpegWrapper transcodes flac to opus"
    ffmpeg = FFmpegWrapper(self.INPUT_FLAC, metadata=self.METADATA)
    output_file = Path(self.TEMPDIR.name) / 'test_a.opus'
    ffmpeg.appendOutputOpus(output_file)
    ffmpeg.run()
    self.assertTrue(output_file.is_file())

  def test_transcode_flac_all(self):
    "FFmpegWrapper transcodes flac to all output formats simultaneously"
    ffmpeg = FFmpegWrapper(self.INPUT_FLAC, metadata=self.METADATA, loglevel='info')
    output_file_opus = Path(self.TEMPDIR.name) / 'test_all.opus'
    ffmpeg.appendOutputOpus(output_file_opus)
    output_file_mp3 = Path(self.TEMPDIR.name) / 'test_all.mp3'
    ffmpeg.appendOutputLame(output_file_mp3)
    output_file_copy = Path(self.TEMPDIR.name) / 'test_all.flac'
    ffmpeg.appendOutputCopy(output_file_copy)
    ffmpeg.run()


class TestR128gainWrapper(unittest.TestCase):
  """ Test r128gain command wrapper against an empty temp dir """
  def test_invocation(self):
    "Invoke a R128gainWrapper"
    with tempfile.TemporaryDirectory('bulklift_tests_') as t:
      ecr = R128gainWrapper(target_dir=t, dry_run=True)
      ecr.run()
    with self.assertRaises(CalledProcessError):
      ecr = R128gainWrapper(
        dry_run=True,
        ffmpeg_binary='/non/existent/ffmpeg098'  # intentionally break it
      )
      result = ecr.run()
