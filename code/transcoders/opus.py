from transcoders.base import TranscoderBase


class TranscoderOpus(TranscoderBase):

  FILE_EXTENSION = '.opus'
  COMMENT = "Bulklift 0.1 (ffmpeg + libopus)"


  def buildTranscodeCmd(self, source_path):
    """ Return a command appropriate for transcoding the specified file """
    return [
      self.ffmpeg_path,
      '-y', '-loglevel', 'error',
      '-i', str(source_path),
      '-c:v', 'copy',
      '-codec:a', 'libopus',
      '-compression_level', '10', # Slowest encode, highest quality
      '-vbr', 'on',
      '-b:a', str(self.output_spec['opus_bitrate']),
      '-map_metadata', '0',
      '-id3v2_version', '3',
      '-write_id3v1', '1',
      '-metadata', 'comment={}'.format(self.COMMENT),
      str(self.outputFilePath(source_path.name))
    ]


  def codecSignature(self):
    """ Return a string representing the codec & settings used to transcode
        the output.  This can be used to detect when the target is outdated and
        needs regenerating.  """
    return super(TranscoderOpus, self).codecSignature() + \
      (self.output_spec['opus_bitrate'],)


  def __str__(self):
    return "<{} output:{} br:{}>".format(
      self.__class__.__name__,
      self.output_name,
      self.output_spec['opus_bitrate']
    )
