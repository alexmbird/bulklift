import os
import os.path
from pathlib import Path
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import yaml
from copy import deepcopy

from clint.textui import indent, puts, colored

from util import dict_not_nulls, filename_matches_globs


# Filetypes that can be transcoded
TRANSCODE_TYPES = ('.flac', '.mp3', '.m4a', '.opus')

# Filetypes that will be directly copied - typically album art
PRESERVE_TYPES = ('.gif', '.jpg', '.jpeg', '.png')


class TranscodingError(Exception):
  "Failure within a transcoding job"


class MetadataError(KeyError):
  "A required piece of metadata was absent"


class TranscoderBase(object):

  SIGNATURE_FILE_NAME = '.bulklift.sig'
  FILE_EXTENSION = 'test'


  def __init__(self, source, metadata, output_name, output_spec, config):
    super(TranscoderBase, self).__init__()
    self.source = source
    self.metadata = metadata
    self.output_name = output_name
    self.output_spec = output_spec
    self.config = config

    # Determine where our output is going
    self.output_path = Path(os.path.expandvars(self.output_spec['path'])).resolve()
    try:
      album_dir = self.config['target']['album_dir'].format(**metadata)
    except KeyError:
      raise MetadataError("{} has malformed metadata: {}".format(self.source.path, metadata))
    self.output_album_path = self.output_path / album_dir

    # Find the binaries we will call.  If missing, better to find out before
    # starting a lengthy transcode job.
    self.ffmpeg_path = self._getBinary('ffmpeg')
    self.r128gain_path = self._getBinary('r128gain')

    # Calculate signatures
    self.signatures = {
      'codec': sha256(yaml.safe_dump(self.codecSignature(), encoding='utf8')).hexdigest(),
      'media': sha256(yaml.safe_dump(self.mediaSignature(), encoding='utf8')).hexdigest(),
      'metadata': sha256(yaml.safe_dump(self.metadata, encoding='utf8')).hexdigest()
    }


  def _getBinary(self, binary):
    """ Return path to user-selected binary or first found in $PATH """
    try:
      found = os.path.expandvars(self.config['binaries'][binary])
      if not (os.path.isfile(found) and os.access(found, os.X_OK)):
        raise FileNotFoundError(
          "user-configured {} binary not present or executable".format(found)
        )
    except KeyError:
      found = shutil.which(binary)
      if found is None:
        raise FileNotFoundError("cannot find a {} binary in your path".format(binary))
    return found


  def outputFileName(self, source_file):
    pre, ext = os.path.splitext(source_file)
    return '.'.join([pre, self.FILE_EXTENSION])


  def makeOutputDir(self):
    """ Make the output dir we'll be transcoding content into """
    shutil.rmtree(str(self.output_album_path), ignore_errors=True)
    self.output_album_path.mkdir(parents=True, exist_ok=True)
    puts("Created dest dir '{}'".format(self.output_album_path))


  def transcode(self, retain_on_fail=False):
    """ Create the appropriate version of the content """
    puts("Transcoding album from {}".format(self.source.path))
    self.makeOutputDir()
    try:
      self.copyPreservedFiles()
      self.transcodeMediaFiles()
      self.r128gain()
      self.writeSignatures()
    except Exception as e:
      if retain_on_fail:
        puts(colored.red("Won't delete broken target dir in --debug mode; be sure to tidy it up manually"))
      else:
        puts(colored.red("Transcoding failed; unlinking output path"))
        shutil.rmtree(str(self.output_album_path), ignore_errors=True)
      raise


  def sourcePreservedFiles(self):
    """ Return a list of the files we should copy unchanged from the source
        directory.  Sorted so a change in filesystem can't change the hash. """
    return sorted([
      p for p in self.source.path.iterdir()
      if p.is_file()
        and p.suffix in PRESERVE_TYPES
        and not p.name.startswith('.')
    ])


  def copyPreservedFiles(self):
    """ Copy static content (e.g. album art) into the output dir """
    for path_src in self.sourcePreservedFiles():
      path_dst = self.output_album_path / path_src.name
      puts("Copying '{}'".format(path_src.name))
      shutil.copy(
        str(path_src),
        str(path_dst)
      )


  def sourceMediaFiles(self):
    """ Return a list of files in the source directory that we should
        transcode.  Sorted so a change in filesystem can't change the hash. """
    candidates = [
      p for p in self.source.path.iterdir()
      if p.is_file()
        and p.suffix in TRANSCODE_TYPES
        and not p.name.startswith('.')
    ]

    # Include only files matching the include glob(s)
    f_include = self.output_spec['filters']['include']
    if f_include:
      candidates = [c for c in candidates if filename_matches_globs(c, f_include)]

    # Filter out any files matching the exclude globs
    f_exclude = self.output_spec['filters']['exclude']
    if f_exclude:
      candidates = [c for c in candidates if not filename_matches_globs(c, f_exclude)]

    # Fin!  Return sorted descending by size, so we process the largest files
    # first.  This makes the most efficient use of all our cores by retaining
    # the smallest jobs to be fed into spare processors at the end.
    return sorted(candidates, key=lambda c: c.stat().st_size, reverse=True)


  def transcodeMediaFiles(self):
    """ Using a ffmpeg command supplied by the Transcoder* implementation
        transcode the relevant set of media files, running multiple transcoders
        in parallel if desired.  """
    files_transcode = self.sourceMediaFiles()
    def _tc(source_p):
      puts("Transcoding '{}'".format(source_p.name))
      return subprocess.run(self.buildTranscodeCmd(source_p))
    with ThreadPoolExecutor(max_workers=self.config['ffmpeg']['threads']) as pool:
      futures = [pool.submit(_tc, p) for p in files_transcode]
      try:
        for future in as_completed(futures):
          cp = future.result()
          if cp.returncode != 0:
            puts(colored.red("Failed '{}'".format(Path(cp.args[-1]).name)))
      except KeyboardInterrupt as e:
        for future in futures:
          future.cancel()
        # Re-raising the exception blows up threading real bad.  Make new one.
        raise TranscodingError("Keyboard interrupt; aborted transcoding")


  def r128gain(self):
    """ Run the r128gain tool over the completed output dir """
    r128_threads = self.config['r128gain']['threads']
    cmd = [
      self.r128gain_path,
      '--recursive', '--ffmpeg-path', self.ffmpeg_path,
      '--opus-output-gain', '--verbosity', 'warning',
    ]
    if self.output_spec['gain']['album']:
      cmd += ['--album-gain']
    # if r128_threads is not None:
    #   cmd += ['--thread-count', str(r128_threads)]
    cmd += [str(self.output_album_path)]
    puts("Running r128gain on output dir (album:{}, threads:{})".format(
      self.output_spec['gain']['album'],
      r128_threads if r128_threads is not None else '?'
    ))
    try:
      cp = subprocess.run(cmd)
    except KeyboardInterrupt:
      raise TranscodingError("Keyboard interrupt; aborted transcoding")
    if cp.returncode == 0:
      puts("Added replaygain tags")
    else:
      raise TranscodingError("Failed to add replaygain tags")


  def buildTranscodeCmd(self, source_path):
    """ Return a command appropriate for transcoding the specified file.
        Override to suit in transcoder implementations.  """
    raise NotImplementedError()


  def codecSignature(self):
    """ Return a string representing the codec & settings used to transcode
        the output.  This can be used to detect when the target is outdated and
        needs regenerating.  Overload in child classes to add more fields.  """
    return (
      self.__class__.__name__,
      self.output_spec['codec_version'],
      self.output_spec['gain']
    )


  def mediaSignature(self):
    """ Return a string representing the contents of files that will be
        transcoded.  This can be used to detect when the target is outdated and
        needs regenerating.  Rather than hashing terabytes of media on every
        run we use the name + mtime of the file.  Move your library with care!
    """
    paths = self.sourcePreservedFiles() + self.sourceMediaFiles()
    name_mtimes = [(p.name, p.stat().st_mtime) for p in paths]
    return sorted(name_mtimes)


  def writeSignatures(self):
    signature_path = self.output_album_path / self.SIGNATURE_FILE_NAME
    puts("Writing {}".format(signature_path))
    with signature_path.open('w') as stream:
      stream.write(yaml.safe_dump(self.signatures))


  def is_stale(self):
    """ Return True if the target is absent or stale """
    signature_path = self.output_album_path / self.SIGNATURE_FILE_NAME
    try:
      with signature_path.open('r', encoding='utf8') as stream:
        old_sig = yaml.safe_load(stream)
    except FileNotFoundError:
      return True  # no signature, definitely stale
    return old_sig != self.signatures


  def dumpInfo(self):
    """ Print info about this transcoder's targets """
    puts("Input:  {}".format(self.source.path))
    puts("Output: {}".format(self.output_album_path))
    puts("Spec:")
    spec = dict_not_nulls(self.output_spec)
    with indent(2):
      puts(yaml.safe_dump(dict_not_nulls(spec)).strip())
    puts("Metadata:")
    with indent(2):
      puts(yaml.safe_dump(dict_not_nulls(spec)).strip())
    puts("Signatures:")
    with indent(2):
      for k, v in self.signatures.items():
        puts("{}: {}".format(k,v))


  def __str__(self):
    return "<{} output:{}>".format(self.__class__.__name__, self.output_name)
