import subprocess as sp
from itertools import chain


class ExternalCommandError(Exception):
  "An error was detected with an external command"


class NothingToDoError(ExternalCommandError):
  "There was no work for the command to do"


class ExternalCommandWrapper(object):
  """ Wrap external commands with checking & arg-handling logic """

  DEFAULT_BINARY = '/bin/true'

  def __init__(self, binary=None, args=[], expected_outputs=[]):
    """ Initialize the wrapper for arbitrary external commands """
    super(ExternalCommandWrapper, self).__init__()

    self.binary = binary if binary is not None else self.DEFAULT_BINARY
    self.args = [self.binary] + args
    self.expected_outputs = list(expected_outputs) # copy it!

  def run(self, output=False):
    """ Execute the wrapped command in a subprocess """
    if output:
      print("cmd is {}".format(self.args))
      print("expected_outputs is {}".format(self.expected_outputs))
    cp = sp.run(self.args, check=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if not all([p.is_file() for p in self.expected_outputs]):
      raise ExternalCommandError("An expected output file was not created")
    if output:
      print("STDOUT: {}".format(cp.stdout))
      print("STDERR: {}".format(cp.stderr))
    return cp

  def __len__(self):
    """ Return the number of files this job is expected to create """
    return len(self.expected_outputs)


class SoxWrapper(ExternalCommandWrapper):
  """ Wrap the sox audio utility; used to create dummy audio files for the
      unit tests.  Not used for actual transcoding. """

  # See http://billposer.org/Linguistics/Computation/SoxTutorial.html

  DEFAULT_BINARY = '/usr/bin/sox'

  def __init__(self, output_path, duration=5, binary=None):
    """ Initialize the wrapper for sox """
    super(SoxWrapper, self).__init__(binary=binary)
    # self.args += [        # silence; r128gain barfs on this
    #   '-n', '-r', '48000',
    #   str(output_path),
    #   "trim", "0.0", str(duration)
    # ]
    self.args += [          # instead let's use a 1khz sine wave
      '-n', '-r', '48000',
      str(output_path), 'synth', str(duration), 'sine', '1000.0'
    ]


class R128gainWrapper(ExternalCommandWrapper):
  """ Wrap the r128gain utility """

  DEFAULT_BINARY = '/usr/local/bin/r128gain'

  def __init__(self, target_dir='.', album_gain=True, threads=None,
               ffmpeg_binary=None, verbosity='warning', dry_run=False,
               binary=None):
    """ Initialize the r128gain wrapper """
    super(R128gainWrapper, self).__init__(binary=binary)
    self.args += chain.from_iterable([
      ['--opus-output-gain', '--recursive'],
      ['--verbosity', verbosity],
      ['--ffmpeg-path', ffmpeg_binary] if ffmpeg_binary else [],
      ['--dry-run'] if dry_run else [],
      ['--album-gain'] if album_gain else [],
      ['--thread-count', str(threads)] if threads else [],
      [str(target_dir)]
    ])


class FFmpegWrapper(ExternalCommandWrapper):
  """ Wrap ffmpeg, with methods to add multiple output files """

  DEFAULT_BINARY = '/usr/bin/ffmpeg'

  def __init__(self, source_path, metadata={}, loglevel='error', binary=None):
    """ Initialize the ffmpeg wrapper """
    super(FFmpegWrapper, self).__init__(binary=binary)
    self.source_path = source_path
    self.args += ['-y', '-loglevel', loglevel, '-i', str(source_path)]
    self.args_metadata = self.metadataOpts(metadata)
    self.output_codecs = []

  def run(self, *args, **kwargs):
    """ run() method overridden to create destination dirs and raise an error
        if the operation wouldn't generate any outputs.  """
    if len(self.expected_outputs) == 0:
      raise NothingToDoError("No outputs to transcode")
    for output_path in self.expected_outputs:
      output_path.parent.mkdir(parents=True, exist_ok=True)
    super(FFmpegWrapper, self).run(*args, **kwargs)

  @staticmethod
  def metadataOpts(metadata={}):
    """ Translate a dict of metadata into ffmpeg -metadata foo=bar options """
    return list(chain.from_iterable(
      [
        ('-metadata', '{}={}'.format(k,v), '-metadata:s:a', '{}={}'.format(k,v))
        for k, v in metadata.items()
      ]
    ))

  def appendOutputCopy(self, output_path):
    """ Add arguments to write a file with same codec as input """
    self.args += ['-map', '0:a']
    self.args += ['-codec:a', 'copy']
    self.args += self.args_metadata
    self.args += [str(output_path)]
    self.expected_outputs.append(output_path)
    self.output_codecs.append('copy')

  def appendOutputLame(self, output_path, vbr=3):
    """ Add arguments to write an mp3 file """
    self.args += ['-map', '0:a']
    self.args += ['-codec:a', 'libmp3lame', '-q:a', str(vbr)]
    self.args += self.args_metadata
    self.args += ['-id3v2_version', '3', '-write_id3v1', '1', '-write_xing', '1']
    self.args += [str(output_path)]
    self.expected_outputs.append(output_path)
    self.output_codecs.append('mp3')

  def appendOutputOpus(self, output_path, bitrate='128k'):
    """ Add arguments to write an opus file """
    self.args += ['-map', '0:a']
    self.args += ['-codec:a', 'libopus']
    self.args += ['-compression_level', '10', '-vbr', 'on', '-b:a', str(bitrate)]
    self.args += self.args_metadata
    self.args += [str(output_path)]
    self.expected_outputs.append(output_path)
    self.output_codecs.append('opus')
