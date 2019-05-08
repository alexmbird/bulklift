import os
import os.path
import shutil
import subprocess
from multiprocessing.pool import ThreadPool

from clint.textui import indent, puts, colored

from util import file_ext_match, dict_deep_get


class TranscoderBase(object):

  # Filetypes that will be transcoded into the output format
  TRANSCODE_TYPES = ('.flac', '.mp3', '.m4a', '.opus')

  # Filetypes that will be directly copied - typically album art
  PRESERVE_TYPES = ('.gif', '.jpg', '.jpeg', '.png')


  OUTPUT_DIR_TEMPLATE = "{genre}/{artist}/{year} {album}"
  FILE_EXTENSION = 'test'


  def __init__(self, source, metadata, output_spec, config):
    super(TranscoderBase, self).__init__()
    self.source = source
    self.metadata = metadata
    self.output_spec = output_spec
    self.config = config

    # Determine where our output is going
    self.output_path = os.path.expandvars(dict_deep_get(self.output_spec, ('path',)))
    self.output_album_dir = self.OUTPUT_DIR_TEMPLATE.format(**self.metadata)
    self.output_album_path = os.path.join(self.output_path, self.output_album_dir)

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
    os.makedirs(self.output_album_path, self.output_dir_mode, exist_ok=False)
    puts("Created dest dir '{}'".format(self.output_album_dir))


  def transcode(self):
    """ Create the appropriate version of the content """
    try:
      self.makeOutputDir()
    except OSError:
      puts("Dest dir '{}' already exists; skipping".format(self.output_album_dir))
      return
    try:
      self.copyPreservedFiles()
      self.transcodeMediaFiles()
      self.r128gain()
      self.setOutputPermissions()
    except Exception:
      puts(colored.red("Unlinking output path"))
      os.unlink(self.output_album_dir)
      raise


  def copyPreservedFiles(self):
    """ Copy static content (e.g. album art) into the output dir """
    files_copy = [
      d.name for d in os.scandir(self.source.path)
      if d.is_file()
        and file_ext_match(self.PRESERVE_TYPES, d.name)
        and not d.name.startswith('.')
    ]
    for name in files_copy:
      source_path = os.path.join(self.source.path, name)
      target_path = os.path.join(self.output_album_path, name)
      puts("Copying '{}'".format(name))
      shutil.copy(source_path, target_path)


  def transcodeMediaFiles(self):
    files_transcode = [
      d.name for d in os.scandir(self.source.path)
      if d.is_file()
        and file_ext_match(self.TRANSCODE_TYPES, d.name)
        and not d.name.startswith('.')
    ]
    cmds = [self.buildTranscodeCmd(name) for name in files_transcode]
    with ThreadPool() as pool:
      puts("Transcoding...")
      result = pool.map_async(subprocess.run, cmds)
      pool.close()
      pool.join()
      for cp in result.get():
        head, tail = os.path.split(cp.args[-1])
        if cp.returncode == 0:
          puts("Transcoded '{}'".format(tail))
        else:
          puts(colored.red("Failed '{}'".format(tail)))


  def r128gain(self):
    """ Run the r128gain tool over the completed output dir """
    cmd = [
      self.r128gain_path,
      '--ffmpeg-path', self.ffmpeg_path,
      '--opus-output-gain',
      '--recursive',
      '--verbosity', 'warning',
      self.output_album_path
    ]
    if self.r128gain_album:
      cmd.insert(1, '--album-gain')
    puts("Running r128gain on output dir")
    cp = subprocess.run(cmd)
    if cp.returncode == 0:
      puts("Added replaygain tags")
    else:
      puts(colored.red("Failed to add replaygain tags"))


  def setOutputPermissions(self):
    """ Set desired perms / ownership on output dir and its contents """
    os.chmod(self.output_album_path, self.output_dir_mode)
    for d in os.scandir(self.output_album_path):
      os.chmod(os.path.join(self.output_album_path, d.name), self.output_file_mode)
    if self.output_user or self.output_group:
      shutil.chown(self.output_album_path, user=self.output_user, group=self.output_group)
      for d in os.scandir(self.output_album_path):
        shutil.chown(os.path.join(self.output_album_path, d.name), user=self.output_user, group=self.output_group)


  def buildTranscodeCmd(self, name):
    """ Return a command appropriate for transcoding the specified file.
        Override to suit in transcoder implementations.  """
    raise NotImplementedError()


  def __str__(self):
    return "<{} writing to '{}'>".format(self.__class__.__name__, self.output_path)
