from transcoders.base import TranscoderBase


class TranscoderOpus(TranscoderBase):

  FILE_EXTENSION = '.opus'


  def buildTranscodeCmd(self, source_path):
    """ Return a command appropriate for transcoding the specified file """
    return [
      self.transcode_ffmpeg_path,
      '-y', '-loglevel', 'error',
      '-i', str(source_path),
      '-map', '0:a',
      # '-map', '0:v?',  # ffmpeg+libopus doesn't like embedded artwork?
      '-codec:a', 'libopus',
      '-codec:v', 'copy',
      '-compression_level', '10', # Slowest encode, highest quality
      '-vbr', 'on',
      '-b:a', str(self.output_spec['opus_bitrate']),
      *self.ffmpegMetadataOptions(),
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
