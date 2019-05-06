import os.path

from util import dict_deep_get

from transcoders.base import TranscoderBase


class TranscoderOpus(TranscoderBase):

  FILE_EXTENSION = 'opus'
  COMMENT = "Bulklift 0.1 (ffmpeg + libopus)"


  def __init__(self, *args, **kwargs):
    super(TranscoderOpus, self).__init__(*args, **kwargs)
    self.opus_bitrate = dict_deep_get(self.output_spec, ('opus_bitrate',), default='128k')


  def buildTranscodeCmd(self, name):
    """ Return a command appropriate for transcoding the specified file """
    source_path = os.path.join(self.source.path, name)
    target_path = os.path.join(self.output_album_path, self.outputFileName(name))
    return [
      self.ffmpeg_path,
      '-y', '-loglevel', 'error',
      '-i', source_path,
      '-c:v', 'copy',
      '-codec:a', 'libopus',
      '-compression_level', '10', # Slowest encode, highest quality
      '-vbr', 'on',
      '-b:a', str(self.opus_bitrate),
      '-map_metadata', '0',
      '-id3v2_version', '3',
      '-write_id3v1', '1',
      '-metadata', 'comment={}'.format(self.COMMENT),
      target_path
    ]


  def __str__(self):
    return "<{} writing to '{}' br:{}>".format(
      self.__class__.__name__,
      self.output_path,
      self.opus_bitrate
    )
