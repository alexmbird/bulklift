from transcoders.base import TranscoderBase


class TranscoderLame(TranscoderBase):

  FILE_EXTENSION = '.mp3'


  def buildTranscodeCmd(self, source_path):
    """ Return a command appropriate for transcoding the specified file """
    return [
      self.transcode_ffmpeg_path,
      '-y', '-loglevel', 'error',
      '-i', str(source_path),
      '-map', '0:a',
      '-map', '0:v?',  # typically embedded artwork
      '-codec:a', 'libmp3lame',
      '-codec:v', 'copy',
      '-q:a', str(self.output_spec['lame_vbr']),
      *self.ffmpegMetadataOptions(),
      '-id3v2_version', '3',
      '-write_id3v1', '1',
      '-write_xing', '1',
      str(self.outputFilePath(source_path.name))
    ]


  def codecSignature(self):
    """ Return a string representing the codec & settings used to transcode
        the output.  This can be used to detect when the target is outdated and
        needs regenerating.  """
    return super(TranscoderLame, self).codecSignature() + \
      (self.output_spec['lame_vbr'],)


  def __str__(self):
    return "<{} output:{} vbr:{}>".format(
      self.__class__.__name__,
      self.output_name,
      self.output_spec['lame_vbr']
    )
