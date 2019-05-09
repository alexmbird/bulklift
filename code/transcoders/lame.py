from util import dict_deep_get

from transcoders.base import TranscoderBase


class TranscoderLame(TranscoderBase):

  FILE_EXTENSION = 'mp3'
  COMMENT = "Bulklift 0.1 (ffmpeg + libmp3lame)"


  def __init__(self, *args, **kwargs):
    super(TranscoderLame, self).__init__(*args, **kwargs)
    self.lame_vbr = dict_deep_get(self.output_spec, ('lame_vbr',), default='3')


  def buildTranscodeCmd(self, source_path):
    """ Return a command appropriate for transcoding the specified file """
    target_path = self.output_album_path / self.outputFileName(source_path.name)
    return [
      self.ffmpeg_path,
      '-y', '-loglevel', 'error',
      '-i', str(source_path),
      '-c:v', 'copy',
      '-codec:a', 'libmp3lame',
      '-q:a', str(self.lame_vbr),
      '-map_metadata', '0',
      '-id3v2_version', '3',
      '-write_id3v1', '1',
      '-metadata', 'comment={}'.format(self.COMMENT),
      str(target_path)
    ]


  def __str__(self):
    return "<{} output:{} vbr:{}>".format(
      self.__class__.__name__,
      self.output_name,
      self.lame_vbr
    )
