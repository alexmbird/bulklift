import os
import os.path
from pathlib import Path
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import yaml

from clint.textui import indent, puts, colored

from util import dict_deep_get


# Filetypes that can be transcoded
TRANSCODE_TYPES = ('.flac', '.mp3', '.m4a', '.opus')

# Filetypes that will be directly copied - typically album art
PRESERVE_TYPES = ('.gif', '.jpg', '.jpeg', '.png')


class TranscodingError(Exception):
  "Failure within a transcoding job"


class TranscoderBase(object):

  OUTPUT_DIR_TEMPLATE = "{genre}/{artist}/{year} {album}"
  FILE_EXTENSION = 'test'
  SIGNATURE_FILE_NAME = '.bulklift.sig'


  def __init__(self, source, metadata, output_name, output_spec, config):
    super(TranscoderBase, self).__init__()
    self.source = source
    self.metadata = metadata
    self.output_name = output_name
    self.output_spec = output_spec
    self.config = config

    try:
      self.thread_count = len(os.sched_getaffinity(0))
    except AttributeError:
      self.thread_count = os.cpu_count()

    # Determine where our output is going
    self.output_path = Path(os.path.expandvars(dict_deep_get(self.output_spec, ('path',)))).resolve()
    self.output_album_path = self.output_path / self.OUTPUT_DIR_TEMPLATE.format(**self.metadata)

    # Find the binaries we will call
    self.ffmpeg_path = self._getFfmpegBinary()
    if self.ffmpeg_path is None:
      sys.exit("Fatal: no ffmpeg binary available")
    self.r128gain_path = self._getR128gainBinary()
    if self.r128gain_path is None:
      sys.exit("Fatal: no r128gain binary available")

    # Determine some other settings
    self.r128gain_album = dict_deep_get(self.output_spec, ('gain', 'album'), True)
    self.output_dir_mode = \
      int(dict_deep_get(self.output_spec, ('permissions', 'dir_mode'), default='0750'), 8)
    self.output_file_mode = \
      int(dict_deep_get(self.output_spec, ('permissions', 'file_mode'), default='0750'), 8)
    self.output_user = dict_deep_get(self.output_spec, ('permissions', 'user'), default=None)
    self.output_group = dict_deep_get(self.output_spec, ('permissions', 'group'), default=None)

    # Calculate signatures
    self.signatures = {
      'codec': sha256(yaml.safe_dump(self.codecSignature(), encoding='utf8')).hexdigest(),
      'media': sha256(yaml.safe_dump(self.mediaSignature(), encoding='utf8')).hexdigest(),
      'metadata': sha256(yaml.safe_dump(self.metadata, encoding='utf8')).hexdigest()
    }


  def _getFfmpegBinary(self):
    try:
      return os.path.expandvars(
        dict_deep_get(self.config, ('binaries', 'ffmpeg'))
      )
    except KeyError:
      return shutil.which('ffmpeg')


  def _getR128gainBinary(self):
    try:
      return os.path.expandvars(
        dict_deep_get(self.config, ('binaries', 'r128gain'))
      )
    except KeyError:
      return shutil.which('r128gain')


  def outputFileName(self, source_file):
    pre, ext = os.path.splitext(source_file)
    return '.'.join([pre, self.FILE_EXTENSION])


  def makeOutputDir(self):
    """ Make the output dir we'll be transcoding content into """
    shutil.rmtree(str(self.output_album_path), ignore_errors=True)
    self.output_album_path.mkdir(self.output_dir_mode, parents=True, exist_ok=True)
    puts("Created dest dir '{}'".format(self.output_album_path))


  def transcode(self):
    """ Create the appropriate version of the content """
    puts("Transcoding album from {}".format(self.source.path))
    self.makeOutputDir()
    try:
      self.copyPreservedFiles()
      self.transcodeMediaFiles()
      self.r128gain()
      self.writeSignatures()
      self.setOutputPermissions()
    except Exception as e:
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
    return sorted([
      p for p in self.source.path.iterdir()
      if p.is_file()
        and p.suffix in TRANSCODE_TYPES
        and not p.name.startswith('.')
    ])


  def transcodeMediaFiles(self):
    """ Using a ffmpeg command supplied by the Transcoder* implementation
        transcode the relevant set of media files, running multiple transcoders
        in parallel if desired.  """
    files_transcode = self.sourceMediaFiles()
    def _tc(source_p):
      puts("Transcoding '{}'".format(source_p.name))
      return subprocess.run(self.buildTranscodeCmd(source_p))
    with ThreadPoolExecutor(max_workers=self.thread_count) as pool:
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
    cmd = [
      self.r128gain_path,
      '--ffmpeg-path', self.ffmpeg_path,
      '--opus-output-gain',
      '--thread-count', str(self.thread_count),
      '--recursive',
      '--verbosity', 'warning',
      str(self.output_album_path)
    ]
    if self.r128gain_album:
      cmd.insert(1, '--album-gain')
    puts("Running r128gain on output dir")
    try:
      cp = subprocess.run(cmd)
    except KeyboardInterrupt:
      raise TranscodingError("Keyboard interrupt; aborted transcoding")
    if cp.returncode == 0:
      puts("Added replaygain tags")
    else:
      raise TranscodingError("Failed to add replaygain tags")


  def setOutputPermissions(self):
    """ Set desired perms / ownership on output dir and its contents """
    self.output_album_path.chmod(self.output_dir_mode)
    if self.output_user or self.output_group:
      shutil.chown(str(self.output_album_path), user=self.output_user, group=self.output_group)
    for p in self.output_album_path.iterdir():
      p.chmod(self.output_file_mode)
      if self.output_user or self.output_group:
        shutil.chown(str(p), user=self.output_user, group=self.output_group)
    puts("Set permissions on output files")


  def buildTranscodeCmd(self, source_path):
    """ Return a command appropriate for transcoding the specified file.
        Override to suit in transcoder implementations.  """
    raise NotImplementedError()


  def codecSignature(self):
    """ Return a string representing the codec & settings used to transcode
        the output.  This can be used to detect when the target is outdated and
        needs regenerating.  """
    raise NotImplementedError()


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
    with indent(2):
      puts(yaml.safe_dump(self.output_spec).strip())
    puts("Metadata:")
    with indent(2):
      puts(yaml.safe_dump(self.metadata).strip())
    puts("Signatures:")
    with indent(2):
      for k, v in self.signatures.items():
        puts("{}: {}".format(k,v))


  def __str__(self):
    return "<{} output:{}>".format(self.__class__.__name__, self.output_name)
