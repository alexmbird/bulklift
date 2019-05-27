""" Output handlers - drop-in classes to submit a transcoding output to ffmpeg
    in the manner appropriate for its format """

from util.sanitize import dummy_sanitize


class OutputHandlerBase(object):
  """ Abstract base for all output handlers """

  FILE_EXTENSION = 'unknown'

  def __init__(self, source_path, output_dir, output_config,
               sanitize=dummy_sanitize):
    """ Initialize the output handler """
    super(OutputHandlerBase, self).__init__()
    self.source_path = source_path
    self.output_path = output_dir / sanitize(self.makeOutputFilename())
    self.output_config = output_config

  def makeOutputFilename(self):
    """ Return the appropriate filename for this output """
    return self.source_path.with_suffix('.' + self.FILE_EXTENSION).name

  def addToFFmpeg(self, ffmpeg):
    """ Add transcoding job to ffmpeg in the appropriate way """
    raise NotImplementedError()

  @property
  def output_name(self):
    return self.output_path.name



class OutputHandlerCopy(OutputHandlerBase):
  """ Handler for bitstream copies """

  def makeOutputFilename(self):
    """ Return the appropriate filename for this output """
    ext = self.source_path.suffix.lower()
    return self.source_path.with_suffix(
      self.source_path.suffix.lower()
    ).name

  def addToFFmpeg(self, ffmpeg):
    """ Add a bitstream copy output to ffmpeg """
    ffmpeg.appendOutputCopy(output_path=self.output_path)


class OutputHandlerOpus(OutputHandlerBase):
  """ Handler for opus files """

  FILE_EXTENSION = 'opus'

  def addToFFmpeg(self, ffmpeg):
    """ Add an opus output to ffmpeg """
    ffmpeg.appendOutputOpus(
      output_path = self.output_path,
      bitrate = self.output_config['opus_bitrate']
    )


class OutputHandlerMp3(OutputHandlerBase):
  """ Handler for mp3 files """

  FILE_EXTENSION = 'mp3'

  def addToFFmpeg(self, ffmpeg):
    """ Add an mp3 output to ffmpeg """
    ffmpeg.appendOutputLame(
      output_path = self.output_path,
      vbr=self.output_config['lame_vbr']
    )


FORMAT_HANDLERS = {
  'copy': OutputHandlerCopy,
  'opus': OutputHandlerOpus,
  'mp3': OutputHandlerMp3
}
