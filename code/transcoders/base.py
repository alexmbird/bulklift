import os
import os.path
import shutil
import subprocess
from multiprocessing.pool import ThreadPool

from clint.textui import indent, puts

from util import file_ext_match, dict_deep_get


class TranscoderBase(object):

  # Filetypes that will be transcoded into the output format
  TRANSCODE_TYPES = ('.flac', '.mp3', '.m4a', '.opus')

  # Filetypes that will be directly copied - typically album art
  PRESERVE_TYPES = ('.gif', '.jpg', '.jpeg', '.png')


  OUTPUT_DIR_TEMPLATE = "__{genre}/{artist}/{year} {album}"
  FILE_EXTENSION = 'test'


  def __init__(self, source, metadata, output_spec, config):
    super(TranscoderBase, self).__init__()
    self.source = source
    self.metadata = metadata
    self.output_spec = output_spec
    self.config = config

    self.output_dir_name = os.path.join(
      dict_deep_get(self.output_spec, ('path',)),
      self.OUTPUT_DIR_TEMPLATE.format(**self.metadata)
    )

    # Find the binaries we will call
    self.ffmpeg_path = self._getFfmpegBinary()
    if self.ffmpeg_path is None:
      sys.exit("Fatal: no ffmpeg binary available")
    else:
      puts("Using ffmpeg {}".format(self.ffmpeg_path))
    self.r128gain_path = self._getR128gainBinary()
    if self.r128gain_path is None:
      sys.exit("Fatal: no r128gain binary available")
    else:
      puts("Using r128gain {}".format(self.r128gain_path))

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
      return dict_deep_get(self.config, ('binaries', 'ffmpeg'))
    except KeyError:
      return shutil.which('ffmpeg')


  def _getR128gainBinary(self):
    try:
      return dict_deep_get(self.config, ('binaries', 'r128gain'))
    except KeyError:
      return shutil.which('r128gain')


  def outputFileName(self, source_file):
    pre, ext = os.path.splitext(source_file)
    return '.'.join([pre, self.FILE_EXTENSION])


  def makeOutputDir(self):
    """ Make the output dir we'll be transcoding content into """
    os.makedirs(self.output_dir_name, self.output_dir_mode, exist_ok=False)


  def transcode(self):
    """ Create the appropriate version of the content """
    try:
      self.makeOutputDir()
    except OSError:
      puts("Target dir already exists; skipping")
      return
    self.copyPreservedFiles()
    self.transcodeMediaFiles()
    self.r128gain()
    self.setOutputPermissions()


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
      target_path = os.path.join(self.output_dir_name, name)
      puts("COPY  '{}' -> '{}'".format(source_path, target_path))
      shutil.copy(source_path, target_path)
      os.chmod(target_path, self.output_file_mode)


  def transcodeMediaFiles(self):
    files_transcode = [
      d.name for d in os.scandir(self.source.path)
      if d.is_file()
        and file_ext_match(self.TRANSCODE_TYPES, d.name)
        and not d.name.startswith('.')
    ]
    cmds = [self.buildTranscodeCmd(name) for name in files_transcode]
    run = lambda cmd: subprocess.run(cmd, check=True)
    with ThreadPool(processes=os.cpu_count()) as pool:
      pool.map(run, cmds)   # should use map_async with a callout to note errors
      pool.close()
      pool.join()


  def r128gain(self):
    """ Run the r128gain tool over the completed output dir """
    cmd = [
      self.r128gain_path,
      '--ffmpeg-path', self.ffmpeg_path,
      '--opus-output-gain',
      '--recursive',
      '--verbosity', 'warning',
      self.output_dir_name
    ]
    if self.r128gain_album:
      cmd.insert(1, '--album-gain')
    subprocess.run(cmd, check=True)


  def setOutputPermissions(self):
    """ Set desired perms / ownership on output dir and its contents """
    os.chmod(self.output_dir_name, self.output_dir_mode)
    for d in os.scandir(self.output_dir_name):
      os.chmod(os.path.join(self.output_dir_name, d.name), self.output_file_mode)
    if self.output_user or self.output_group:
      shutil.chown(self.output_dir_name, user=self.output_user, group=self.output_group)
      for d in os.scandir(self.output_dir_name):
        shutil.chown(os.path.join(self.output_dir_name, d.name), user=self.output_user, group=self.output_group)


  def buildTranscodeCmd(self, name):
    """ Return a command appropriate for transcoding the specified file.
        Override to suit in transcoder implementations.  """
    raise NotImplementedError()


  def __str__(self):
    return "<{} writing to '{}'>".format(self.__class__.__name__, self.output_dir_name)
